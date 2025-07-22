import json
import logging
from typing import List, Dict, Any, Optional

from openai import OpenAI, AsyncOpenAI

from .config import Config
from .discourse import DiscoursePost, DiscourseSearcher
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

You have access to the following tools:

### search_discourse
Search the Discourse forum for topics related to the user's query.
- **query** (string): The search query to execute
- **Returns**: A list of up to 6 relevant forum topics with their titles, URLs, and first 1000 characters of content

### send_link
Send a link to the user when you find a relevant topic.
- **url** (string): The URL of the relevant topic
- **message** (string): A brief message indicating this is the best match found
- **Returns**: Confirmation that the message was sent

### no_result_message
Inform the user when no relevant results could be found.
- **Returns**: Confirmation that the message was sent

## Search Process

1. **Context Analysis**: If you receive a message with both original and reply content, analyze both to understand the full context
2. **Initial Search**: Search the forum using relevant keywords from the context
3. **Evaluate Results**: Review the returned topics to determine if any directly address the user's question
4. **Iterative Search**: If no good results are found, you may perform up to 3 additional searches with refined queries
5. **Decision Point**: After searching, you must either:
   - Call `send_link` with the URL of the most relevant topic
   - Call `no_result_message` if no relevant topics are found

## Response Guidelines

- **Language**: Respond in the same language as the user's query
- **Conciseness**: Keep responses brief and to the point
- **Direct Links**: Only provide the forum link, no additional content from the post
- **Relevance**: Ensure the linked topic directly addresses or is highly relevant to the user's query
- **Context Awareness**: When replying to a conversation, acknowledge the context from previous messages

## Examples

**When a perfect match is found:**
"I found a perfect match for your question: [topic URL]"

**When the closest relevant topic is found:**
"Here's the closest relevant topic I found: [topic URL]"

**When no results are found:**
"I couldn't find any relevant topics for your question. Please try rephrasing your query or visit the forum directly."""
    
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
            
            # Define tools for the LLM - using simpler dict structure
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
                },
                {
                    "type": "function",
                    "function": {
                        "name": "send_link",
                        "description": "Send a link to the user when you find a relevant topic",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "The URL of the relevant topic"
                                },
                                "message": {
                                    "type": "string",
                                    "description": "A brief message indicating this is the best match found"
                                }
                            },
                            "required": ["url", "message"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "no_result_message",
                        "description": "Inform the user when no relevant results could be found",
                        "parameters": {
                            "type": "object",
                            "properties": {}
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
                                # Force no result if max attempts reached
                                logger.llm("Maximum search attempts reached, forcing no result message")
                                final_response = self.response_config.get_error_message("no_results_found")
                                break
                                
                            query = function_args.get("query", "")
                            logger.llm(f"Searching Discourse with query: '{query}'")
                            search_results = await self.discourse_searcher.search(query)
                            logger.llm(f"Discourse search returned {len(search_results)} results")
                            
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
                            
                        elif function_name == "send_link":
                            url = function_args.get("url", "")
                            message = function_args.get("message", "")
                            
                            logger.llm(f"LLM selected URL to send: {url}")
                            logger.llm(f"LLM message: {message}")
                            
                            # Add UTM tags to the URL if configured
                            url_with_utm = self.config.add_utm_tags_to_url(url)
                            if url != url_with_utm:
                                logger.llm(f"URL with UTM tags: {url_with_utm}")
                            
                            final_response = f"{message}\n\n{url_with_utm}"
                            logger.llm(f"Final response prepared: {final_response}")
                            break
                            
                        elif function_name == "no_result_message":
                            logger.llm("LLM determined no relevant results found")
                            final_response = self.response_config.get_error_message("no_results_found")
                            logger.llm(f"No result message: {final_response}")
                            break
                
                # Check if we have a final response
                if final_response:
                    logger.llm("Final response received, ending LLM interaction")
                    break
                
                # If no tool calls and no final response, use the content
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
            
            # Enhanced fallback logging
            if not final_response:
                if search_attempts >= self.max_search_attempts:
                    logger.llm(f"Using fallback response: Maximum search attempts ({self.max_search_attempts}) reached without send_link or no_result_message")
                elif tool_calls_executed:
                    logger.llm("Using fallback response: LLM executed tool calls but never called send_link or no_result_message")
                else:
                    logger.llm("Using fallback response: LLM provided no tool calls and no direct response")
                    
                final_response = self.response_config.get_error_message("fallback_error")
            
            # Log token usage
            if response and hasattr(response, 'usage') and response.usage:
                logger.llm(f"Token usage - prompt: {response.usage.prompt_tokens}, completion: {response.usage.completion_tokens}, total: {response.usage.total_tokens}")
            
            logger.llm(f"Question processing completed successfully")
            return final_response
            
        except Exception as e:
            logger.error(f"Error processing question with tools: {e}", exc_info=True)
            logger.llm(f"LLM processing failed with error: {e}")
            return self.response_config.get_error_message("processing_error")
    
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
    
    # Legacy method for backward compatibility
    async def generate_answer(self, question: str, search_results: List[DiscoursePost]) -> str:
        """
        Legacy method - use process_question_with_tools instead.
        This method is kept for backward compatibility but will be removed.
        """
        logger.warning("Using deprecated generate_answer method")
        return await self.process_question_with_tools(question)
