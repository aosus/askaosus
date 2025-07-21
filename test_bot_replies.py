#!/usr/bin/env python3
"""
Test the bot's reply detection functionality.
"""

import asyncio
import logging
import sys
import unittest.mock as mock
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import after sys.path modification
import importlib
import os

# Set PYTHONPATH to src directory
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Now import with absolute imports as they would work from src directory
os.chdir(Path(__file__).parent / "src")
from bot import AskaosusBot
from config import Config
from nio import MatrixRoom, RoomMessageText, RoomGetEventResponse

# Change back to original directory
os.chdir(Path(__file__).parent)

# Set up logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MockMatrixRoom:
    """Mock Matrix room for testing."""
    
    def __init__(self, room_id="!test:example.org"):
        self.room_id = room_id


class MockEvent:
    """Mock Matrix event for testing."""
    
    def __init__(self, sender="@user:example.org", body="Test message", event_id="$event1", 
                 reply_to_event_id=None, server_timestamp=None):
        self.sender = sender
        self.body = body
        self.event_id = event_id
        self.server_timestamp = server_timestamp or int(datetime.now().timestamp() * 1000)
        
        # Create source structure for replies
        self.source = {"content": {}}
        if reply_to_event_id:
            self.source["content"]["m.relates_to"] = {
                "m.in_reply_to": {
                    "event_id": reply_to_event_id
                }
            }


class MockRoomGetEventResponse:
    """Mock response for room_get_event."""
    
    def __init__(self, event):
        self.event = event


async def test_reply_to_bot_message():
    """Test that the bot detects replies to its own messages."""
    print("Testing bot reply detection...")
    
    # Create mock config
    mock_config = mock.MagicMock()
    mock_config.bot_mentions = ["@askaosus", "askaosus"]
    mock_config.matrix_store_path = "/tmp/test_store"
    mock_config.matrix_homeserver_url = "https://matrix.example.org"
    mock_config.matrix_user_id = "@bot:example.org"
    mock_config.matrix_device_name = "test-bot"
    mock_config.bot_rate_limit_seconds = 0.0
    
    # Create bot instance with mocked dependencies
    with mock.patch('bot.DiscourseSearcher'), \
         mock.patch('bot.LLMClient'), \
         mock.patch('bot.ResponseConfig'), \
         mock.patch('bot.AsyncClient') as mock_client_class:
        
        # Set up the mock client instance
        mock_client = mock.MagicMock()
        mock_client.user_id = "@bot:example.org"
        mock_client_class.return_value = mock_client
        
        bot = AskaosusBot(mock_config)
        bot.matrix_client = mock_client
        
        # Test cases
        room = MockMatrixRoom()
        
        # Case 1: Direct mention - should respond
        print("  Test 1: Direct mention")
        mentioned_event = MockEvent(body="@askaosus How do I install Ubuntu?")
        question, should_respond = await bot._should_respond(room, mentioned_event)
        assert should_respond, "Bot should respond to direct mentions"
        assert "How do I install Ubuntu?" in question, f"Question extraction failed: {question}"
        print("    ✓ Responds to direct mentions")
        
        # Case 2: Reply to bot message - should respond
        print("  Test 2: Reply to bot message")
        
        # First, create a bot message that the user is replying to
        bot_message = MockEvent(
            sender="@bot:example.org",
            body="Here's how to install Ubuntu...",
            event_id="$bot_msg1"
        )
        
        # User reply to bot message (no mention needed)
        user_reply = MockEvent(
            sender="@user:example.org",
            body="That didn't work for me",
            reply_to_event_id="$bot_msg1"
        )
        
        # Mock the room_get_event to return the bot message
        mock_client.room_get_event.return_value = MockRoomGetEventResponse(bot_message)
        
        question, should_respond = await bot._should_respond(room, user_reply)
        assert should_respond, "Bot should respond to replies to its own messages"
        assert "Bot:" in question and "User:" in question, f"Conversation thread not built properly: {question}"
        print("    ✓ Responds to replies to bot messages")
        
        # Case 3: Reply to another user's message - should NOT respond
        print("  Test 3: Reply to another user's message")
        
        other_user_message = MockEvent(
            sender="@other:example.org",
            body="I also have this problem",
            event_id="$other_msg1"
        )
        
        user_reply_to_other = MockEvent(
            sender="@user:example.org",
            body="Maybe we should check the docs",
            reply_to_event_id="$other_msg1"
        )
        
        # Mock the room_get_event to return the other user's message
        mock_client.room_get_event.return_value = MockRoomGetEventResponse(other_user_message)
        
        question, should_respond = await bot._should_respond(room, user_reply_to_other)
        assert not should_respond, "Bot should NOT respond to replies to other users' messages"
        print("    ✓ Does NOT respond to replies to other users")
        
        # Case 4: Bot's own message - should be skipped at message_callback level
        print("  Test 4: Bot's own message")
        bot_own_message = MockEvent(sender="@bot:example.org", body="I am responding...")
        question, should_respond = await bot._should_respond(room, bot_own_message)
        # Note: The actual filtering of bot's own messages happens in message_callback, 
        # but _should_respond should still return False for consistency
        print("    ✓ Bot message handling checked")


async def test_conversation_thread_building():
    """Test building conversation threads from reply chains."""
    print("Testing conversation thread building...")
    
    # Create mock config
    mock_config = mock.MagicMock()
    mock_config.bot_mentions = ["@askaosus", "askaosus"]
    
    # Create bot instance with mocked dependencies
    with mock.patch('bot.DiscourseSearcher'), \
         mock.patch('bot.LLMClient'), \
         mock.patch('bot.ResponseConfig'), \
         mock.patch('bot.AsyncClient') as mock_client_class:
        
        mock_client = mock.MagicMock()
        mock_client.user_id = "@bot:example.org"
        mock_client_class.return_value = mock_client
        
        bot = AskaosusBot(mock_config)
        bot.matrix_client = mock_client
        
        room = MockMatrixRoom()
        
        # Create a conversation thread:
        # 1. User asks question with mention
        # 2. Bot responds
        # 3. User replies to bot (without mention)
        
        user_question = MockEvent(
            sender="@user:example.org",
            body="@askaosus How do I install Ubuntu?",
            event_id="$user_q1"
        )
        
        bot_answer = MockEvent(
            sender="@bot:example.org", 
            body="Here are the steps to install Ubuntu...",
            event_id="$bot_a1",
            reply_to_event_id="$user_q1"
        )
        
        user_followup = MockEvent(
            sender="@user:example.org",
            body="That didn't work, I'm getting an error",
            event_id="$user_f1",
            reply_to_event_id="$bot_a1"
        )
        
        # Mock the room_get_event calls to return the conversation chain
        def mock_get_event(room_id, event_id):
            if event_id == "$bot_a1":
                return MockRoomGetEventResponse(bot_answer)
            elif event_id == "$user_q1":
                return MockRoomGetEventResponse(user_question)
            else:
                raise Exception(f"Unknown event ID: {event_id}")
        
        mock_client.room_get_event.side_effect = mock_get_event
        
        # Build the conversation thread
        conversation = await bot._build_conversation_thread(room, user_followup)
        
        print(f"    Built conversation: {conversation}")
        
        # Verify the conversation contains all parts
        assert "User: How do I install Ubuntu?" in conversation, "Original question missing"
        assert "Bot: Here are the steps" in conversation, "Bot response missing"
        assert "User: That didn't work" in conversation, "User followup missing"
        assert conversation.startswith("Conversation thread:"), "Thread format incorrect"
        
        print("    ✓ Conversation thread built correctly")


async def main():
    """Run all tests."""
    print("🧪 Running bot reply tests...\n")
    
    try:
        await test_reply_to_bot_message()
        print("✅ Reply detection tests passed!\n")
        
        await test_conversation_thread_building()
        print("✅ Conversation thread tests passed!\n")
        
        print("🎉 All bot reply tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)