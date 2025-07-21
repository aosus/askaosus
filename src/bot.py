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
            # Validate timestamp is a reasonable value
            try:
                if isinstance(event.server_timestamp, (int, float)) and event.server_timestamp > 0:
                    if event.server_timestamp < self.start_time:
                        logger.debug(f"Skipping old message from {event.sender}: {event.body[:50] if event.body else '[no body]'}...")
                        return
                else:
                    logger.debug(f"Invalid timestamp format: {event.server_timestamp}")
            except Exception as e:
                logger.debug(f"Error validating timestamp: {e}")
                # Continue processing if timestamp validation fails
        
        # Check rate limiting
        current_time = asyncio.get_event_loop().time()
        if current_time - self.last_message_time < self.config.bot_rate_limit_seconds:
            logger.debug("Rate limit triggered, skipping message")
            return
        
        try:
            # Validate event has required properties
            if not hasattr(event, 'body'):
                logger.debug("Event missing body property")
                return
            
            # Check if the bot should respond to this message
            question, should_respond = await self._should_respond(room, event)
            
            if should_respond and question:
                logger.info(f"Processing question in room {room.room_id}: {question[:100] if len(question) > 100 else question}...")
                
                # Update rate limit
                self.last_message_time = current_time
                
                # Send typing notification
                await self.matrix_client.room_typing(room.room_id, True)
                
                try:
                    # Process the question
                    answer = await self._process_question(question)
                    
                    # Validate answer before sending
                    if not answer or len(answer.strip()) == 0:
                        logger.warning("LLM returned empty answer")
                        answer = "I apologize, but I couldn't generate a proper response. Please try asking your question again."
                    
                    # Convert markdown to HTML for formatted_body
                    formatted_answer = _convert_markdown_to_html(answer)
                    
                    # Send the answer
                    await self.matrix_client.room_send(
                        room_id=room.room_id,
                        message_type="m.room.message",
                        content={
                            "msgtype": "m.text",
                            "body": answer,  # Plain text version
                            "format": "org.matrix.custom.html",
                            "formatted_body": formatted_answer,  # HTML version
                        },
                    )
                    
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
    
    async def _build_conversation_thread(self, room: MatrixRoom, event: RoomMessageText) -> str:
        """
        Build the complete conversation thread by following the reply chain.
        
        This method traces back through the reply chain to find the original message
        and then builds a chronological context of the conversation.
        
        Args:
            room: The Matrix room
            event: The current message event
            
        Returns:
            A formatted string containing the conversation context
        """
        conversation = []
        current_event = event
        
        # Build a list of events by following the reply chain backwards
        events_chain = [current_event]
        
        # Track visited events to prevent infinite loops
        visited_event_ids = {current_event.event_id}
        max_depth = 20  # Reasonable limit for conversation threads
        depth = 0
        
        while depth < max_depth:
            # Validate event structure before accessing
            if not hasattr(current_event, 'source') or not isinstance(current_event.source, dict):
                logger.debug("Event missing source structure, stopping thread building")
                break
                
            content = current_event.source.get('content', {})
            relates_to = content.get('m.relates_to', {})
            
            if 'm.in_reply_to' not in relates_to:
                break
                
            original_event_id = relates_to['m.in_reply_to'].get('event_id')
            if not original_event_id:
                logger.debug("Missing event_id in reply structure")
                break
            
            # Check for cycles
            if original_event_id in visited_event_ids:
                logger.warning(f"Detected reply cycle involving event {original_event_id}, stopping thread building")
                break
            
            try:
                # Add timeout to prevent hanging
                original_response = await asyncio.wait_for(
                    self.matrix_client.room_get_event(room.room_id, original_event_id),
                    timeout=5.0
                )
                
                if isinstance(original_response, RoomGetEventResponse):
                    original_event = original_response.event
                    events_chain.append(original_event)
                    visited_event_ids.add(original_event_id)
                    current_event = original_event
                    depth += 1
                else:
                    logger.debug(f"Failed to fetch event {original_event_id}: {original_response}")
                    break
            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching event {original_event_id}")
                break
            except Exception as e:
                logger.debug(f"Error fetching event {original_event_id}: {e}")
                break
        
        # Reverse the chain to get chronological order (oldest to newest)
        events_chain.reverse()
        
        # Build the conversation context
        for i, evt in enumerate(events_chain):
            if isinstance(evt, RoomMessageText):
                sender_display = "Bot" if evt.sender == self.matrix_client.user_id else "User"
                message_content = evt.body.strip() if evt.body else ""
                
                # For the first message in a thread, remove bot mentions to get clean question
                if i == 0 and sender_display == "User":
                    message_content = self._remove_mentions_from_text(message_content)
                
                # Handle empty messages after mention removal
                if not message_content and i == 0:
                    message_content = "[mention only]"
                
                conversation.append(f"{sender_display}: {message_content}")
            else:
                # Handle non-text events
                event_type = type(evt).__name__
                sender_display = "Bot" if evt.sender == self.matrix_client.user_id else "User"
                conversation.append(f"{sender_display}: [{event_type} - non-text content]")
        
        if len(conversation) > 1:
            context = "Conversation thread:\n" + "\n".join(conversation)
            logger.debug(f"Built conversation thread with {len(conversation)} messages (depth limit: {max_depth})")
            return context
        elif len(conversation) == 1:
            # Single message, just return the content
            return conversation[0].split(": ", 1)[1] if ": " in conversation[0] else conversation[0]
        else:
            # Fallback to current message content
            return event.body.strip() if hasattr(event, 'body') and event.body else "[empty message]"

    def _remove_mentions_from_text(self, text: str) -> str:
        """
        Remove bot mentions from text with improved regex patterns.
        
        Handles edge cases like punctuation and ensures clean output.
        
        Args:
            text: Text containing potential mentions
            
        Returns:
            Text with mentions removed and cleaned up
        """
        if not text:
            return ""
        
        result = text
        for mention in self.config.bot_mentions:
            mention_clean = mention.lstrip('@')  # Remove @ if present
            
            # More precise patterns that handle punctuation correctly
            patterns = [
                rf'@{re.escape(mention_clean)}\b',  # @mention
                rf'\b{re.escape(mention)}\b',       # Full mention as configured
                rf'\b{re.escape(mention_clean)}\b(?=\s*[:\-,])',  # mention followed by punctuation
                rf'\b{re.escape(mention_clean)}(?=\s*$)',  # mention at end of string
            ]
            
            for pattern in patterns:
                result = re.sub(pattern, "", result, flags=re.IGNORECASE)
        
        # Clean up leftover punctuation and whitespace
        result = re.sub(r'^[\s:,\-]+', '', result)  # Remove leading punctuation
        result = re.sub(r'\s*[,]\s+', ' ', result)   # Clean up orphaned commas with spaces
        result = re.sub(r'\s+[,]', ',', result)      # Fix spaced commas 
        result = re.sub(r'\s+', ' ', result)         # Normalize whitespace
        result = result.strip()
        
        return result

    async def _is_reply_to_bot_message(self, room: MatrixRoom, event: RoomMessageText) -> bool:
        """
        Check if the message is a reply to one of the bot's own messages.
        
        Returns:
            True if the message is replying to a bot message, False otherwise
        """
        # Validate event structure
        if not hasattr(event, 'source') or not isinstance(event.source, dict):
            return False
        
        content = event.source.get('content', {})
        relates_to = content.get('m.relates_to', {})
        
        if 'm.in_reply_to' not in relates_to:
            return False
        
        reply_info = relates_to['m.in_reply_to']
        if not isinstance(reply_info, dict) or 'event_id' not in reply_info:
            return False
        
        original_event_id = reply_info['event_id']
        if not original_event_id:
            return False
        
        try:
            # Add timeout to prevent hanging
            original_response = await asyncio.wait_for(
                self.matrix_client.room_get_event(room.room_id, original_event_id),
                timeout=5.0
            )
            
            if isinstance(original_response, RoomGetEventResponse):
                original_event = original_response.event
                # Check if the original message was sent by the bot
                return original_event.sender == self.matrix_client.user_id
        except asyncio.TimeoutError:
            logger.warning(f"Timeout checking if reply is to bot message: {original_event_id}")
            return False
        except Exception as e:
            logger.debug(f"Error checking if reply is to bot message: {e}")
            return False
        
        return False

    async def _should_respond(self, room: MatrixRoom, event: RoomMessageText) -> Tuple[Optional[str], bool]:
        """
        Determine if the bot should respond to a message and extract the question.
        
        Returns:
            Tuple of (question_with_context, should_respond)
        """
        message_body = event.body.strip()
        
        # Check for direct mentions
        bot_mentions = self.config.bot_mentions
        
        # Check if the message mentions the bot
        message_lower = message_body.lower()
        mentioned = any(mention in message_lower for mention in bot_mentions)
        
        # Check if this is a reply to a bot message
        is_reply_to_bot = await self._is_reply_to_bot_message(room, event)
        
        # Respond if either mentioned directly or replying to bot message
        if mentioned or is_reply_to_bot:
            if mentioned:
                # Remove the mention from the message to get the question
                question = self._remove_mentions_from_text(message_body)
                
                # Handle empty messages after mention removal
                if not question:
                    question = "[mention only]"
                
                # Check if this is a reply to another message for context
                replied_to_content = None
                is_reply = False
                
                if hasattr(event, 'source') and isinstance(event.source, dict):
                    content = event.source.get('content', {})
                    relates_to = content.get('m.relates_to', {})
                    if 'm.in_reply_to' in relates_to and relates_to['m.in_reply_to'].get('event_id'):
                        is_reply = True
                        original_event_id = relates_to['m.in_reply_to']['event_id']
                        
                        # Always attempt to fetch the original message for context
                        try:
                            logger.debug(f"Fetching replied-to message: {original_event_id}")
                            original_response = await asyncio.wait_for(
                                self.matrix_client.room_get_event(room.room_id, original_event_id),
                                timeout=5.0
                            )
                            
                            # Check if the response is successful and contains a message event
                            if isinstance(original_response, RoomGetEventResponse):
                                original_event = original_response.event
                                # Handle different types of events
                                if isinstance(original_event, RoomMessageText):
                                    replied_to_content = original_event.body or "[empty message]"
                                    logger.debug(f"Retrieved replied-to message content: {replied_to_content[:100]}...")
                                else:
                                    # Handle non-text events (images, files, etc.)
                                    event_type = type(original_event).__name__
                                    replied_to_content = f"[{event_type} - content not accessible as text]"
                                    logger.debug(f"Original event is not a text message: {event_type}")
                            else:
                                logger.warning(f"Failed to fetch original message {original_event_id}: {original_response}")
                                replied_to_content = "[Original message could not be retrieved]"
                        except asyncio.TimeoutError:
                            logger.warning(f"Timeout fetching replied-to message: {original_event_id}")
                            replied_to_content = "[Original message could not be retrieved - timeout]"
                        except Exception as e:
                            logger.warning(f"Error fetching replied-to message: {e}")
                            replied_to_content = "[Original message could not be retrieved]"
                
                # Always provide context when this is a reply, even if fetching failed
                if is_reply:
                    # Ensure we have some context, even if fetching failed
                    if replied_to_content is None:
                        replied_to_content = "[Original message could not be retrieved]"
                    
                    # Create a context string with both messages
                    full_context = f"Original message: {replied_to_content}\n\nReply: {question}"
                    logger.info("Including replied-to message as context for better understanding")
                    return full_context, True
                elif question:
                    # No replied-to message, just use the mentioning message
                    return question, True
            
            elif is_reply_to_bot:
                # This is a reply to a bot message, build the full conversation thread
                logger.info("Message is a reply to bot message, building conversation thread")
                conversation_context = await self._build_conversation_thread(room, event)
                return conversation_context, True
        
        return None, False
    
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
            return self.response_config.get_error_message("search_error")
