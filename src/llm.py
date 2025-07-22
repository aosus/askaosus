import json
import logging
from typing import List, Dict, Any, Optional

from openai import OpenAI, AsyncOpenAI

from .config import Config
from .discourse import DiscoursePost, DiscourseSearcher, DiscourseRateLimitError, DiscourseConnectionError
from .responses import ResponseConfig
from .logging_utils import get_llm_logger, LLM_LEVEL

logger = get_llm_logger(__name__)


class LLMClient:
    """Handles communication with Language Learning Models using tool calling."""
    
    def __init__(self, config: Config, discourse_searcher: DiscourseSearcher):
        """Initialize the LLM client."""
        self.config = config
        self.discourse_searcher = discourse_searcher
        
        # Initialize response configuration
        self.response_config = ResponseConfig()
        
        # Initialize OpenAI-compatible client
        client_kwargs = config.get_openai_client_kwargs()
        self.client = AsyncOpenAI(**client_kwargs)
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
        
        # Maximum search attempts
        self.max_search_attempts = config.bot_max_search_iterations
    
    def _load_system_prompt(self) -> str:
        """Load the system prompt from file."""
        try:
            with open("/app/system_prompt.md", "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            # Fallback system prompt
            return self._get_default_system_prompt()
    
    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt."""
        return """# System Instructions for Forum AI Assistant

You are an AI assistant for a community forum, specializing in answering questions by searching the Discourse forum. Your role is to help users find relevant information from the community's forum posts.

## Context Understanding

When a user mentions you in response to another message, you will receive both messages as context:
- "Original message: [content of the message being replied to]"
- "Reply: [content of the mentioning message]"

Use both messages to understand the full context of what the user is asking about. The original message provides important background, while the reply contains the specific request or question. This context handling allows for better understanding of conversations and more accurate responses.

**Note**: If the original message could not be retrieved, you'll see "[Original message could not be retrieved]" - in this case, work with the available reply context.

## Available Tools

You have access to the following tool:

### search_discourse
Search the Discourse forum for topics related to the user's query.
- **query** (string): The search query to execute
- **Returns**: A list of up to 6 relevant forum topics with their titles, URLs, and first 1000 characters of content

## Search Process

1. **Context Analysis**: If you receive a message with both original and reply content, analyze both to understand the full context
2. **Initial Search**: Search the forum using relevant keywords from the context
3. **Evaluate Results**: Review the returned topics to determine if any directly address the user's question
4. **Iterative Search**: If no good results are found, you may perform up to 3 additional searches with refined queries
5. **Provide Answer**: After searching, provide a helpful response based on the search results

## Response Guidelines

- **Language**: Respond in the same language as the user's query
- **Helpfulness**: Provide useful answers based on the search results
- **Include Links**: When relevant topics are found, include the topic URLs in your response
- **Relevance**: Ensure your response directly addresses the user's query
- **Context Awareness**: When replying to a conversation, acknowledge the context from previous messages
- **No Results**: If no relevant results are found, inform the user and suggest they visit the forum directly"""""
    
    async def process_question_with_tools(self, question: str) -> str:
        """
        Process a question using LLM with tool calling capabilities.
        
        Args:
            question: The user's question
            
        Returns:
            The final response message
        """
        try:
            logger.llm(f"Processing question with tools: {question}")
            logger.llm(f"System prompt length: {len(self.system_prompt)} characters")
            
            # Define tools for the LLM - only search_discourse
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "search_discourse",
                        "description": "Search the Discourse forum for topics related to the user's query, search using keywords in the query language or in english.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query to execute."
                                }
                            },
                            "required": ["query"]
                        }
                    }
                }
            ]
            
            # Prepare messages - using simple dict structure
            messages: List[Dict[str, Any]] = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": question}
            ]
            
            # Track function calls
            search_attempts = 0
            final_response = None
            response = None
            tool_calls_executed = False
            
            while search_attempts < self.max_search_attempts:
                logger.llm(f"LLM attempt {search_attempts + 1}/{self.max_search_attempts}")
                logger.llm(f"Sending {len(messages)} messages to LLM (model: {self.config.llm_model})")
                
                # Call LLM with tools
                response = await self.client.chat.completions.create(
                    model=self.config.llm_model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=self.config.llm_max_tokens,
                    temperature=self.config.llm_temperature,
                )
                
                message = response.choices[0].message
                
                # Log the LLM response details
                logger.llm(f"LLM response received - finish_reason: {response.choices[0].finish_reason}")
                if message.content:
                    logger.llm(f"LLM response content: {message.content}")
                else:
                    logger.llm("LLM response contains no text content (tool calls only)")
                
                if message.tool_calls:
                    logger.llm(f"LLM requested {len(message.tool_calls)} tool call(s)")
                    for i, tool_call in enumerate(message.tool_calls, 1):
                        logger.llm(f"Tool call {i}: {tool_call.function.name}")
                else:
                    logger.llm("LLM made no tool calls")
                
                # Check if the LLM wants to use tools
                if message.tool_calls:
                    tool_calls_executed = True
                    for tool_call in message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        logger.llm(f"Executing function: {function_name}")
                        logger.debug(f"Function arguments: {function_args}")
                        
                        if function_name == "search_discourse":
                            if search_attempts >= self.max_search_attempts:
                                # Stop searching if max attempts reached
                                logger.llm("Maximum search attempts reached, stopping search")
                                break
                                
                            query = function_args.get("query", "")
                            logger.llm(f"Searching Discourse with query: '{query}'")
                            
                            try:
                                search_results = await self.discourse_searcher.search(query, self.config.bot_max_search_results)
                                logger.llm(f"Discourse search returned {len(search_results)} results")
                            except DiscourseRateLimitError:
                                logger.warning("Discourse rate limit hit during search")
                                return self.response_config.get_error_message("rate_limit_error")
                            except DiscourseConnectionError:
                                logger.warning("Discourse connection error during search")
                                return self.response_config.get_error_message("discourse_unreachable")
                            
                            # Format search results for the LLM
                            search_context = self._format_search_results(search_results)
                            logger.llm(f"Formatted search context length: {len(search_context)} characters")
                            
                            # Log the raw search context being sent to the LLM
                            if search_results:
                                logger.llm("Raw search context sent to LLM:")
                                logger.llm(search_context)
                            else:
                                logger.llm("No search results to send to LLM")
                            
                            messages.append({
                                "role": "assistant",
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": tool_call.id,
                                        "type": "function",
                                        "function": {
                                            "name": function_name,
                                            "arguments": json.dumps(function_args)
                                        }
                                    }
                                ]
                            })
                            
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": search_context
                            })
                            
                            search_attempts += 1
                            logger.llm(f"Search context added to conversation, continuing to next LLM call")
                
                # If no tool calls and we have content, use it as final response
                if message.content and not message.tool_calls:
                    final_response = message.content.strip()
                    logger.llm(f"Using LLM direct response: {final_response}")
                    break
                
                # Log if we're continuing to next iteration
                if message.tool_calls and not final_response:
                    logger.llm("Tool calls executed, continuing to next LLM iteration")
                elif not message.tool_calls and not message.content:
                    logger.llm("LLM returned no tool calls and no content - this may cause fallback")
                    break
            
            # If no final response, provide a fallback
            if not final_response:
                if search_attempts > 0:
                    # Had search results but LLM didn't provide good response
                    final_response = "I searched the forum but couldn't find a good answer to your question. Please try rephrasing or visit the forum directly: https://discourse.aosus.org"
                else:
                    # No searches performed
                    final_response = "I couldn't process your question. Please try again or visit the forum directly: https://discourse.aosus.org"
                
                logger.llm(f"Using fallback response: {final_response}")
            
            # Log token usage
            if response and hasattr(response, 'usage') and response.usage:
                logger.llm(f"Token usage - prompt: {response.usage.prompt_tokens}, completion: {response.usage.completion_tokens}, total: {response.usage.total_tokens}")
            
            logger.llm(f"Question processing completed successfully")
            
            # Apply UTM tags to any URLs in the final response
            final_response = self._add_utm_tags_to_response(final_response)
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error processing question with tools: {e}", exc_info=True)
            logger.llm(f"PROCESSING ERROR - Exception occurred: {type(e).__name__}: {e}")
            return self.response_config.get_error_message("llm_down")
    
    def _format_search_results(self, search_results: List[DiscoursePost]) -> str:
        """Format search results for the LLM."""
        if not search_results:
            return self.response_config.get_discourse_message("no_results")
        
        formatted_results = []
        for i, post in enumerate(search_results, 1):
            formatted_results.append(
                f"Result {i}:\n"
                f"Title: {post.title}\n"
                f"URL: {post.url}\n"
                f"Content: {post.excerpt}\n"
            )
        
        return "\n".join(formatted_results)
    
    def _add_utm_tags_to_response(self, response: str) -> str:
        """Add UTM tags to any URLs found in the response."""
        import re
        
        # Find URLs in the response (basic regex for http/https URLs)
        url_pattern = r'https?://[^\s<>"{}|\\^`[\]]*'
        
        def replace_url(match):
            url = match.group(0)
            return self.config.add_utm_tags_to_url(url)
        
        # Replace all URLs with UTM-tagged versions
        return re.sub(url_pattern, replace_url, response)
    
    # Legacy method for backward compatibility
    async def generate_answer(self, question: str, search_results: List[DiscoursePost]) -> str:
        """
        Legacy method - use process_question_with_tools instead.
        This method is kept for backward compatibility but will be removed.
        """
        logger.warning("Using deprecated generate_answer method")
        return await self.process_question_with_tools(question)
