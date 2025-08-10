import asyncio
import logging
import re
import markdown
from pathlib import Path
from typing import Optional, Tuple

from nio import (
    AsyncClient,
    ClientConfig,
    Event,
    LoginResponse,
    MatrixRoom,
    RoomMessageText,
    SyncResponse,
    RoomGetEventResponse,
)

from .config import Config
from .discourse import DiscourseSearcher
from .llm import LLMClient
from .responses import ResponseConfig

logger = logging.getLogger(__name__)


def _convert_markdown_to_html(text: str) -> str:
    """
    Convert markdown text to HTML suitable for Matrix messages.
    
    This function converts markdown to HTML while ensuring compatibility with
    Matrix's supported HTML subset as defined in the Matrix specification.
    
    Args:
        text: Markdown-formatted text
        
    Returns:
        HTML-formatted text suitable for Matrix formatted_body
    """
    try:
        # Configure markdown with extensions that produce Matrix-compatible HTML
        md = markdown.Markdown(
            extensions=[
                'markdown.extensions.nl2br',      # Convert newlines to <br>
                'markdown.extensions.fenced_code', # Support ```code blocks```
            ],
            # Configure to be more conservative with HTML output
            output_format='html'
        )
        
        # Convert markdown to HTML
        html = md.convert(text)
        
        # Ensure we don't have any disallowed HTML tags or attributes
        # Matrix allows: font, del, h1-h6, blockquote, p, a, ul, ol, sup, sub, li, b, i, u, 
        # strong, em, strike, code, hr, br, div, table, thead, tbody, tr, th, td, caption, pre, span, img
        
        return html
        
    except Exception as e:
        logger.warning(f"Failed to convert markdown to HTML: {e}")
        # Fallback: just convert newlines to <br> tags
        return text.replace('\n', '<br>')


class AskaosusBot:
    """Main bot class for the Askaosus Matrix Bot."""
    
    def __init__(self, config: Config):
        """Initialize the bot with configuration."""
        self.config = config
        self.is_running = False
        
        # Initialize response configuration
        self.response_config = ResponseConfig()
        
        # Initialize Matrix client
        client_config = ClientConfig(
            store_sync_tokens=True,
            encryption_enabled=False,  # Disable encryption for simplicity
        )
        
        self.matrix_client = AsyncClient(
            homeserver=config.matrix_homeserver_url,
            user=config.matrix_user_id,
            device_id=config.matrix_device_name,
            store_path=config.matrix_store_path,
            config=client_config,
        )
        
        # Track when the bot started to ignore old messages
        self.start_time = None
        
        # Track bot messages for reply behavior (store event IDs of messages sent by bot)
        self.bot_message_ids = set()
        
        # Initialize other components
        self.discourse_searcher = DiscourseSearcher(config)
        self.llm_client = LLMClient(config, self.discourse_searcher)
        
        # Rate limiting
        self.last_message_time = 0.0
        
        # Setup event handlers
        self.matrix_client.add_event_callback(self.message_callback, RoomMessageText)
        self.matrix_client.add_response_callback(self.sync_callback, SyncResponse)
    
    async def start(self):
        """Start the bot."""
        try:
            self.is_running = True
            
            # Record the start time to ignore old messages
            import time
            self.start_time = int(time.time() * 1000)  # Convert to milliseconds
            
            # Ensure store directory exists
            Path(self.config.matrix_store_path).mkdir(parents=True, exist_ok=True)
            
            # Login to Matrix
            await self._login()
            
            # Do an initial sync to get up to current state, but don't process messages
            logger.info("Performing initial sync to catch up to current state...")
            await self.matrix_client.sync(timeout=30000, full_state=True)
            
            # Update start time after initial sync to ignore all previous messages
            self.start_time = int(time.time() * 1000)
            logger.info(f"Bot ready to process new messages (start time: {self.start_time})")
            
            # Start syncing and processing new messages
            logger.info("Bot started successfully. Listening for new messages...")
            await self.matrix_client.sync_forever(timeout=30000)
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}", exc_info=True)
            raise
    
    async def shutdown(self):
        """Shutdown the bot gracefully."""
        if self.is_running:
            logger.info("Shutting down bot...")
            self.is_running = False
            # Save session store to preserve login state
            # Attempt to save session store if supported
            save_fn = getattr(self.matrix_client, "save_store", None)
            if callable(save_fn):
                try:
                    save_fn()
                    logger.info("Session store saved successfully")
                except Exception as e:
                    logger.warning(f"Failed to save session store: {e}")
            await self.matrix_client.close()
            logger.info("Bot shutdown complete")
    
    async def _login(self):
        """Login to Matrix server."""
        # Attempt manual session restore from JSON
        # Ensure the session store directory exists
        store_dir = Path(self.config.matrix_store_path)
        store_dir.mkdir(parents=True, exist_ok=True)
        session_file = store_dir / "session.json"
        # Attempt to restore session from JSON file inside matrix_store
        if session_file.exists():
            try:
                import json
                data = json.loads(session_file.read_text(encoding="utf-8"))
                self.matrix_client.user_id = data.get("user_id")
                self.matrix_client.access_token = data.get("access_token")
                self.matrix_client.device_id = data.get("device_id")
                if self.matrix_client.user_id and self.matrix_client.access_token:
                    logger.info("Restored Matrix session from session.json, skipping login")
                    return
            except Exception as e:
                logger.warning(f"Failed to restore session from JSON: {e}")
        else:
            # Ensure store directory exists
            store_dir.mkdir(parents=True, exist_ok=True)
            logger.info("No session.json found, will login and create new session file")
        
        # Login with password
        logger.info("Logging in with password...")
        response = await self.matrix_client.login(
            password=self.config.matrix_password,
            device_name=self.config.matrix_device_name,
        )
        
        if isinstance(response, LoginResponse):
            logger.info(f"Logged in as {self.config.matrix_user_id}")
            # Save session credentials to JSON for future restores
            try:
                import json
                session_file.write_text(
                    json.dumps({
                        "user_id": self.matrix_client.user_id,
                        "access_token": self.matrix_client.access_token,
                        "device_id": self.matrix_client.device_id,
                    }), encoding="utf-8"
                )
                logger.info("Session saved to session.json")
            except Exception as e:
                logger.warning(f"Failed to write session.json: {e}")
        else:
            logger.error(f"Login failed: {response}")
            raise Exception(f"Login failed: {response}")
    
    async def sync_callback(self, response: SyncResponse):
        """Handle sync responses."""
        if response.next_batch:
            # Save the sync token
            pass
    
    async def message_callback(self, room: MatrixRoom, event: Event):
        """Handle incoming messages."""
        # Skip if the bot sent this message
        if event.sender == self.matrix_client.user_id:
            return
        
        # Skip if not a text message
        if not isinstance(event, RoomMessageText):
            return
        
        # Skip old messages (messages sent before bot started)
        if self.start_time and hasattr(event, 'server_timestamp') and event.server_timestamp:
            if event.server_timestamp < self.start_time:
                logger.debug(f"Skipping old message from {event.sender}: {event.body[:50]}...")
                return
        
        # Check rate limiting
        current_time = asyncio.get_event_loop().time()
        if current_time - self.last_message_time < self.config.bot_rate_limit_seconds:
            logger.debug("Rate limit triggered, skipping message")
            return
        
        try:
            # Check if the bot should respond to this message
            result = await self._should_respond(room, event)
            question, should_respond, reply_to_event_id = result
            
            if should_respond and question:
                logger.info(f"Processing question in room {room.room_id}: {question[:100]}...")
                
                # Update rate limit
                self.last_message_time = current_time
                
                # Send typing notification
                await self.matrix_client.room_typing(room.room_id, True)
                
                try:
                    # Process the question
                    answer = await self._process_question(question)
                    
                    # Convert markdown to HTML for formatted_body
                    formatted_answer = _convert_markdown_to_html(answer)
                    
                    # Prepare message content
                    content = {
                        "msgtype": "m.text",
                        "body": answer,  # Plain text version
                        "format": "org.matrix.custom.html",
                        "formatted_body": formatted_answer,  # HTML version
                    }
                    
                    # Add reply information if this is a response to a reply
                    if reply_to_event_id:
                        content["m.relates_to"] = {
                            "m.in_reply_to": {
                                "event_id": reply_to_event_id
                            }
                        }
                    
                    # Send the answer
                    response = await self.matrix_client.room_send(
                        room_id=room.room_id,
                        message_type="m.room.message",
                        content=content,
                    )
                    
                    # Track this bot message for reply behavior
                    if hasattr(response, 'event_id') and response.event_id:
                        self.bot_message_ids.add(response.event_id)
                        logger.debug(f"Tracking bot message: {response.event_id}")
                    
                    logger.info(f"Sent answer in room {room.room_id}")
                    
                finally:
                    # Stop typing notification
                    await self.matrix_client.room_typing(room.room_id, False)
        
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            # Stop typing notification on error
            try:
                await self.matrix_client.room_typing(room.room_id, False)
            except:
                pass
    
    async def _get_thread_context(self, room: MatrixRoom, event_id: str, max_depth: int = 6) -> list:
        """
        Traverse a reply thread up to a specified depth and collect message context.
        
        Args:
            room: The Matrix room
            event_id: The event ID to start traversal from
            max_depth: Maximum number of messages to collect
            
        Returns:
            List of message contents in chronological order (oldest first)
        """
        thread_messages = []
        current_event_id = event_id
        depth = 0
        
        while current_event_id and depth < max_depth:
            try:
                logger.debug(f"Fetching thread message {depth + 1}/{max_depth}: {current_event_id}")
                response = await self.matrix_client.room_get_event(room.room_id, current_event_id)
                
                if not isinstance(response, RoomGetEventResponse):
                    logger.warning(f"Failed to fetch thread message {current_event_id}: {response}")
                    break
                
                event = response.event
                
                # Process the message content
                if isinstance(event, RoomMessageText):
                    content = event.body
                else:
                    event_type = type(event).__name__
                    content = f"[{event_type} - content not accessible as text]"
                
                # Add to thread messages (we'll reverse later for chronological order)
                thread_messages.append({
                    'content': content,
                    'event_id': current_event_id,
                    'sender': getattr(event, 'sender', 'unknown'),
                    'is_bot_message': current_event_id in self.bot_message_ids
                })
                
                depth += 1
                
                # Check if this message is also a reply
                next_event_id = None
                if hasattr(event, 'source') and 'content' in event.source:
                    content_data = event.source['content']
                    if 'm.relates_to' in content_data and 'm.in_reply_to' in content_data['m.relates_to']:
                        next_event_id = content_data['m.relates_to']['m.in_reply_to']['event_id']
                
                current_event_id = next_event_id
                
            except Exception as e:
                logger.warning(f"Error fetching thread message {current_event_id}: {e}")
                break
        
        # Reverse to get chronological order (oldest first)
        thread_messages.reverse()
        
        logger.debug(f"Collected {len(thread_messages)} messages in thread")
        return thread_messages
    
    async def _should_respond(self, room: MatrixRoom, event: RoomMessageText) -> Tuple[Optional[str], bool, Optional[str]]:
        """
        Determine if the bot should respond to a message and extract the question.
        
        Returns:
            Tuple of (question_with_context, should_respond, reply_to_event_id)
        """
        message_body = event.body.strip()
        bot_mentions = self.config.bot_mentions
        
        # Check if the message mentions the bot
        # Use formatted body that excludes replied-to content, or clean quoted lines from raw body
        mentioned = self._check_message_mentions_bot(message_body, bot_mentions, event)
        
        # Check if this is a reply to another message
        is_reply = False
        original_event_id = None
        replied_to_content = None
        is_reply_to_bot = False
        
        if hasattr(event, 'source') and 'content' in event.source:
            content = event.source['content']
            if 'm.relates_to' in content and 'm.in_reply_to' in content['m.relates_to']:
                is_reply = True
                original_event_id = content['m.relates_to']['m.in_reply_to']['event_id']
                
                # Check if this is a reply to a bot message
                is_reply_to_bot = original_event_id in self.bot_message_ids
                
                # Fetch the original message for context
                try:
                    logger.debug(f"Fetching replied-to message: {original_event_id}")
                    original_response = await self.matrix_client.room_get_event(room.room_id, original_event_id)
                    
                    if isinstance(original_response, RoomGetEventResponse):
                        original_event = original_response.event
                        if isinstance(original_event, RoomMessageText):
                            replied_to_content = original_event.body
                            logger.debug(f"Retrieved replied-to message content: {replied_to_content[:100]}...")
                        else:
                            event_type = type(original_event).__name__
                            replied_to_content = f"[{event_type} - content not accessible as text]"
                            logger.debug(f"Original event is not a text message: {event_type}")
                    else:
                        logger.warning(f"Failed to fetch original message {original_event_id}: {original_response}")
                        replied_to_content = "[Original message could not be retrieved]"
                except Exception as e:
                    logger.warning(f"Error fetching replied-to message: {e}")
                    replied_to_content = "[Original message could not be retrieved]"
        
        # Handle different reply behaviors
        reply_behavior = self.config.bot_reply_behavior
        
        # Case 1: This is a reply to a bot message
        if is_reply and is_reply_to_bot:
            logger.debug(f"Message is a reply to bot message. Reply behavior: {reply_behavior}")
            
            if reply_behavior == "ignore":
                # Ignore all replies to bot messages, even if they mention the bot
                logger.debug("Ignoring reply to bot message due to 'ignore' reply behavior")
                return None, False, None
            
            elif reply_behavior == "mention":
                # Only respond to replies to bot messages if they also mention the bot
                if not mentioned:
                    logger.debug("Ignoring reply to bot message without mention due to 'mention' reply behavior")
                    return None, False, None
                # Fall through to process the reply with mention
            
            elif reply_behavior == "watch":
                # Respond to all replies to bot messages regardless of mentions
                # In watch mode, use thread context to provide full conversation history
                pass  # Fall through to process the reply
            
            # Clean up the message body by removing Matrix reply formatting
            cleaned_body = self._clean_reply_content(message_body, bot_mentions)
            
            # Prepare context based on reply behavior
            if reply_behavior == "watch":
                # In watch mode, get full thread context
                try:
                    logger.info(f"Collecting thread context (up to {self.config.bot_thread_depth_limit} messages)")
                    thread_messages = await self._get_thread_context(room, original_event_id, self.config.bot_thread_depth_limit)
                    
                    if thread_messages:
                        # Format thread context with chronological messages
                        context_parts = []
                        for i, msg in enumerate(thread_messages):
                            sender_label = "Bot" if msg['is_bot_message'] else "User"
                            context_parts.append(f"Message {i+1} ({sender_label}): {msg['content']}")
                        
                        # Add the current reply at the end
                        context_parts.append(f"Current reply: {cleaned_body}")
                        
                        full_context = "\n\n".join(context_parts)
                        logger.info(f"Processing reply with {len(thread_messages)} thread messages as context")
                    else:
                        # Fallback to single message context if thread collection failed
                        if replied_to_content is None:
                            replied_to_content = "[Original message could not be retrieved]"
                        full_context = f"Original message: {replied_to_content}\n\nReply: {cleaned_body}"
                        logger.info("Using fallback single message context")
                        
                except Exception as e:
                    logger.warning(f"Failed to collect thread context: {e}")
                    # Fallback to single message context
                    if replied_to_content is None:
                        replied_to_content = "[Original message could not be retrieved]"
                    full_context = f"Original message: {replied_to_content}\n\nReply: {cleaned_body}"
                    logger.info("Using fallback single message context due to thread collection error")
            else:
                # For mention mode, use single message context (original behavior)
                if replied_to_content is None:
                    replied_to_content = "[Original message could not be retrieved]"
                full_context = f"Original message: {replied_to_content}\n\nReply: {cleaned_body}"
                logger.info("Processing reply to bot message with single message context")
            
            return full_context, True, event.event_id
        
        # Case 2: This is a reply to a non-bot message
        elif is_reply and not is_reply_to_bot:
            # For replies to non-bot messages, only respond if mentioned (original behavior)
            if mentioned:
                logger.debug("Processing reply to non-bot message with mention")
                question = message_body
                for mention in bot_mentions:
                    question = re.sub(rf"\b{re.escape(mention)}\b", "", question, flags=re.IGNORECASE)
                question = question.strip()
                
                # Provide context with original message
                if replied_to_content is None:
                    replied_to_content = "[Original message could not be retrieved]"
                
                full_context = f"Original message: {replied_to_content}\n\nReply: {question}"
                logger.info("Processing reply to non-bot message with mention and context")
                return full_context, True, event.event_id
            else:
                logger.debug("Ignoring reply to non-bot message without mention")
                return None, False, None
        
        # Case 3: This is a direct message (not a reply)
        elif mentioned:
            # Remove the mention from the message to get the question
            question = message_body
            for mention in bot_mentions:
                question = re.sub(rf"\b{re.escape(mention)}\b", "", question, flags=re.IGNORECASE)
            question = question.strip()
            
            if question:
                logger.debug("Processing direct mention")
                return question, True, event.event_id
        
        # Default: don't respond
        return None, False, None
    
    def _check_message_mentions_bot(self, message_body: str, bot_mentions: list, event: RoomMessageText = None) -> bool:
        """
        Check if a message mentions the bot, excluding quoted content.
        
        This method ensures that only direct mentions in the actual message content
        are detected, not mentions that appear in quoted/replied-to content.
        
        Matrix clients typically include quoted content in the 'body' field but 
        exclude it from the 'formatted_body' field for replies. We prefer
        formatted_body when available.
        
        Args:
            message_body: The raw message body
            bot_mentions: List of bot mention strings to check for
            event: The Matrix event (optional, for accessing formatted_body)
            
        Returns:
            True if the message directly mentions the bot (not in quoted content)
        """
        # Prefer formatted_body if available, as it excludes replied-to content  
        content_to_check = message_body
        
        if event and hasattr(event, 'formatted_body') and event.formatted_body:
            # Use formatted_body but strip HTML tags for text-based mention detection
            import re
            # Simple HTML tag removal - convert <br> to newlines and remove other tags
            formatted_content = event.formatted_body
            formatted_content = re.sub(r'<br\s*/?>', '\n', formatted_content, flags=re.IGNORECASE)
            formatted_content = re.sub(r'<[^>]+>', '', formatted_content)
            # Decode HTML entities
            import html
            formatted_content = html.unescape(formatted_content).strip()
            
            if formatted_content:
                content_to_check = formatted_content
                logger.debug(f"Using formatted_body for mention detection: {len(formatted_content)} chars")
            else:
                logger.debug("formatted_body was empty, falling back to body")
        else:
            logger.debug("No formatted_body available, using raw body with quote filtering")
        
        # If we're using raw body, remove quoted lines (fallback for clients that don't use formatted_body)
        if content_to_check == message_body:
            lines = message_body.split('\n')
            non_quote_lines = []
            for line in lines:
                # Skip lines that are Matrix quote replies (fallback formatting)
                if not line.strip().startswith('> '):
                    non_quote_lines.append(line)
            content_to_check = '\n'.join(non_quote_lines).strip()
        
        # Check for mentions in the cleaned content only
        content_lower = content_to_check.lower()
        mentioned = any(mention.lower() in content_lower for mention in bot_mentions)
        
        logger.debug(f"Mention detection: original_length={len(message_body)}, "
                    f"content_length={len(content_to_check)}, mentioned={mentioned}")
        
        return mentioned
    
    def _clean_reply_content(self, message_body: str, bot_mentions: list) -> str:
        """
        Clean reply content by removing Matrix reply formatting and bot mentions.
        
        Args:
            message_body: The raw message body
            bot_mentions: List of bot mention strings to remove
            
        Returns:
            Cleaned message content
        """
        cleaned = message_body
        
        # Remove bot mentions - handle @ symbols properly
        for mention in bot_mentions:
            if mention.startswith('@'):
                # For @mentions, remove the whole word
                cleaned = re.sub(rf"@{re.escape(mention[1:])}\b", "", cleaned, flags=re.IGNORECASE)
            # Also handle the mention without @ in case it's in the list
            cleaned = re.sub(rf"\b{re.escape(mention)}\b", "", cleaned, flags=re.IGNORECASE)
        
        # Remove common Matrix reply prefixes (fallback formatting)
        # This removes lines that start with "> " which are quote replies
        lines = cleaned.split('\n')
        non_quote_lines = []
        for line in lines:
            # Skip lines that are Matrix quote replies
            if not line.strip().startswith('> '):
                non_quote_lines.append(line)
        
        cleaned = '\n'.join(non_quote_lines).strip()
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    async def _process_question(self, question: str) -> str:
        """Process a question using the new LLM tool-calling approach."""
        try:
            logger.info(f"Processing question: {question}")
            
            # Use the new tool-calling approach
            answer = await self.llm_client.process_question_with_tools(question)
            
            logger.info("Successfully processed question with tools")
            return answer
            
        except Exception as e:
            logger.error(f"Error processing question: {e}", exc_info=True)
            return self.response_config.get_error_message("llm_down")
