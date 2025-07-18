import asyncio
import logging
import re
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
)

from .config import Config
from .discourse import DiscourseSearcher
from .llm import LLMClient

logger = logging.getLogger(__name__)


class AskaosusBot:
    """Main bot class for the Askaosus Matrix Bot."""
    
    def __init__(self, config: Config):
        """Initialize the bot with configuration."""
        self.config = config
        self.is_running = False
        
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
            question, should_respond = await self._should_respond(room, event)
            
            if should_respond and question:
                logger.info(f"Processing question in room {room.room_id}: {question[:100]}...")
                
                # Update rate limit
                self.last_message_time = current_time
                
                # Send typing notification
                await self.matrix_client.room_typing(room.room_id, True)
                
                try:
                    # Process the question
                    answer = await self._process_question(question)
                    
                    # Send the answer
                    await self.matrix_client.room_send(
                        room_id=room.room_id,
                        message_type="m.room.message",
                        content={
                            "msgtype": "m.text",
                            "body": answer,
                            "format": "org.matrix.custom.html",
                            "formatted_body": answer.replace("\n", "<br>"),
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
    
    async def _should_respond(self, room: MatrixRoom, event: RoomMessageText) -> Tuple[Optional[str], bool]:
        """
        Determine if the bot should respond to a message and extract the question.
        
        Returns:
            Tuple of (question, should_respond)
        """
        message_body = event.body.strip()
        
        # Check for direct mentions
        bot_mentions = ["@askaosus", "askaosus"]
        
        # Check if the message mentions the bot
        message_lower = message_body.lower()
        mentioned = any(mention in message_lower for mention in bot_mentions)
        
        if mentioned:
            # Remove the mention from the message to get the question
            question = message_body
            for mention in bot_mentions:
                question = re.sub(rf"\b{re.escape(mention)}\b", "", question, flags=re.IGNORECASE)
            question = question.strip()
            
            # If there's still content after removing mentions, use it as the question
            if question:
                return question, True
        
        # Check if this is a reply to another message and the reply mentions the bot
        if hasattr(event, 'source') and 'content' in event.source:
            content = event.source['content']
            if 'm.relates_to' in content:
                relates_to = content['m.relates_to']
                if relates_to.get('rel_type') == 'm.replace' or 'in_reply_to' in relates_to:
                    # This is a reply, check if it mentions the bot
                    if mentioned:
                        # Get the original message being replied to
                        try:
                            original_event_id = relates_to.get('in_reply_to', {}).get('event_id')
                            if original_event_id:
                                # We can use the replied-to message as context
                                # For now, just use the reply text as the question
                                question = re.sub(r"^> .*\n", "", message_body, flags=re.MULTILINE)
                                for mention in bot_mentions:
                                    question = re.sub(rf"\b{re.escape(mention)}\b", "", question, flags=re.IGNORECASE)
                                question = question.strip()
                                
                                if question:
                                    return question, True
                        except Exception as e:
                            logger.debug(f"Error processing reply: {e}")
        
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
            return "عذراً، حدث خطأ أثناء البحث عن إجابة. يرجى المحاولة مرة أخرى لاحقاً أو زيارة مجتمع أسس مباشرة: https://discourse.aosus.org"
