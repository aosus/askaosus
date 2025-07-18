import json
import logging
from typing import List, Dict, Any, Optional

from openai import OpenAI, AsyncOpenAI

from .config import Config
from .discourse import DiscoursePost, DiscourseSearcher

logger = logging.getLogger(__name__)


class LLMClient:
    """Handles communication with Language Learning Models using tool calling."""
    
    def __init__(self, config: Config, discourse_searcher: DiscourseSearcher):
        """Initialize the LLM client."""
        self.config = config
        self.discourse_searcher = discourse_searcher
        
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
        return """# System Instructions for Askaosus AI Assistant

You are an AI assistant for the Askaosus community, the largest Arabic community for free and open-source software. Your role is to help users find relevant information from the community's Discourse forum.

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

1. **Initial Search**: Start by searching the Discourse forum using the user's exact query
2. **Evaluate Results**: Review the returned topics to determine if any directly address the user's question
3. **Iterative Search**: If no good results are found, you may perform up to 3 additional searches with refined queries
4. **Decision Point**: After searching, you must either:
   - Call `send_link` with the URL of the most relevant topic
   - Call `no_result_message` if no relevant topics are found

## Response Guidelines

- **Language**: Always respond in Arabic
- **Conciseness**: Keep responses brief and to the point
- **Direct Links**: Only provide the forum link, no additional content from the post
- **Relevance**: Ensure the linked topic directly addresses or is highly relevant to the user's query

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
            logger.info(f"Processing question with tools: {question}")
            
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
            
            while search_attempts < self.max_search_attempts:
                logger.info(f"LLM attempt {search_attempts + 1}")
                
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
                
                # Check if the LLM wants to use tools
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        logger.info(f"LLM called function: {function_name}")
                        logger.debug(f"Function arguments: {function_args}")
                        
                        if function_name == "search_discourse":
                            if search_attempts >= self.max_search_attempts:
                                # Force no result if max attempts reached
                                final_response = "عذراً، لم أتمكن من العثور على موضوعات ذات صلة بسؤالك. يرجى المحاولة بصيغة مختلفة أو زيارة المنتدى مباشرة: https://discourse.aosus.org"
                                break
                                
                            query = function_args.get("query", "")
                            search_results = await self.discourse_searcher.search(query)
                            
                            # Format search results for the LLM
                            search_context = self._format_search_results(search_results)
                            
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
                            
                        elif function_name == "send_link":
                            url = function_args.get("url", "")
                            message = function_args.get("message", "")
                            final_response = f"{message}\n\n{url}"
                            break
                            
                        elif function_name == "no_result_message":
                            final_response = "عذراً، لم أتمكن من العثور على موضوعات ذات صلة بسؤالك. يرجى المحاولة بصيغة مختلفة أو زيارة المنتدى مباشرة: https://discourse.aosus.org"
                            break
                
                # Check if we have a final response
                if final_response:
                    break
                
                # If no tool calls and no final response, use the content
                if message.content and not message.tool_calls:
                    final_response = message.content.strip()
                    break
            
            # Fallback if no response generated
            if not final_response:
                final_response = "عذراً، لم أتمكن من معالجة سؤالك. يرجى المحاولة مرة أخرى أو زيارة المنتدى مباشرة: https://discourse.aosus.org"
            
            # Log token usage
            if response and hasattr(response, 'usage') and response.usage:
                logger.info(f"Token usage - prompt: {response.usage.prompt_tokens}, completion: {response.usage.completion_tokens}, total: {response.usage.total_tokens}")
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error processing question with tools: {e}", exc_info=True)
            return "عذراً، حدث خطأ أثناء معالجة سؤالك. يرجى المحاولة مرة أخرى أو زيارة المنتدى مباشرة: https://discourse.aosus.org"
    
    def _format_search_results(self, search_results: List[DiscoursePost]) -> str:
        """Format search results for the LLM."""
        if not search_results:
            return "No relevant topics found."
        
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
