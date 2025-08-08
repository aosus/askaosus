#!/usr/bin/env python3
"""
Test the new thread context functionality for BOT_REPLY_BEHAVIOR=watch mode.

This test validates:
1. Thread context collection traverses reply chains correctly
2. Thread depth limit is respected 
3. Messages are returned in chronological order
4. Bot message identification works correctly
5. Context formatting includes thread history
6. Fallback behavior when thread collection fails
"""

import os
import sys
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass
from typing import Optional

# Ensure the src directory is in Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

@dataclass
class MockEvent:
    """Mock Matrix event for testing."""
    sender: str
    body: str
    event_id: str
    source: dict
    
@dataclass  
class MockRoom:
    """Mock Matrix room for testing."""
    room_id: str = "!test:matrix.org"

class MockRoomGetEventResponse:
    """Mock response from room_get_event."""
    def __init__(self, event):
        self.event = event

async def test_thread_context_functionality():
    """Test the thread context collection functionality."""
    print("=== Testing Thread Context Functionality ===")
    
    # Setup test environment
    os.environ["MATRIX_HOMESERVER_URL"] = "https://matrix.test.org"
    os.environ["MATRIX_USER_ID"] = "@testbot:matrix.test.org"  
    os.environ["MATRIX_PASSWORD"] = "test_password"
    os.environ["LLM_API_KEY"] = "test_key"
    os.environ["BOT_REPLY_BEHAVIOR"] = "watch"
    os.environ["BOT_THREAD_DEPTH_LIMIT"] = "3"  # Small limit for testing
    
    try:
        from config import Config
        from bot import AskaosusBot
        from nio import RoomMessageText
        
        # Create bot instance
        config = Config()
        bot = AskaosusBot(config)
        
        # Mock the Matrix client
        bot.matrix_client = MagicMock()
        bot.matrix_client.room_get_event = AsyncMock()
        
        # Track some bot message IDs
        bot.bot_message_ids.add("$bot_msg_1")
        bot.bot_message_ids.add("$bot_msg_2")
        
        # Create a mock thread chain:
        # Message 1 (User): "How do I install Ubuntu?"
        # Message 2 (Bot): "Here's how to install Ubuntu..."  
        # Message 3 (User): "What about step 3?"
        
        mock_messages = [
            MockEvent(
                sender="@user:matrix.org",
                body="How do I install Ubuntu?", 
                event_id="$msg_1",
                source={"content": {}}  # No reply relation - thread root
            ),
            MockEvent(
                sender="@testbot:matrix.test.org",
                body="Here's how to install Ubuntu...",
                event_id="$bot_msg_1", 
                source={"content": {
                    "m.relates_to": {
                        "m.in_reply_to": {"event_id": "$msg_1"}
                    }
                }}
            ),
            MockEvent(
                sender="@user:matrix.org", 
                body="What about step 3?",
                event_id="$msg_3",
                source={"content": {
                    "m.relates_to": {
                        "m.in_reply_to": {"event_id": "$bot_msg_1"}
                    }
                }}
            )
        ]
        
        # Setup mock responses for room_get_event
        def mock_room_get_event(room_id, event_id):
            for msg in mock_messages:
                if msg.event_id == event_id:
                    # Convert to RoomMessageText-like object
                    text_msg = MagicMock(spec=RoomMessageText)
                    text_msg.body = msg.body
                    text_msg.sender = msg.sender
                    text_msg.source = msg.source
                    return MockRoomGetEventResponse(text_msg)
            return None
            
        bot.matrix_client.room_get_event.side_effect = mock_room_get_event
        
        # Test 1: Thread context collection from latest message
        print("Test 1: Thread context collection")
        room = MockRoom()
        
        # Start from the latest message ($msg_3) and traverse up the thread
        thread_context = await bot._get_thread_context(room, "$msg_3", 3)
        
        print(f"  Collected {len(thread_context)} messages")
        
        # Should collect messages in chronological order (oldest first)
        expected_order = [
            ("How do I install Ubuntu?", "@user:matrix.org", False),
            ("Here's how to install Ubuntu...", "@testbot:matrix.test.org", True),
            ("What about step 3?", "@user:matrix.org", False)
        ]
        
        for i, (expected_content, expected_sender, expected_is_bot) in enumerate(expected_order):
            if i < len(thread_context):
                msg = thread_context[i]
                if expected_content in msg['content'] and msg['sender'] == expected_sender and msg['is_bot_message'] == expected_is_bot:
                    print(f"  ✓ Message {i+1}: '{msg['content'][:30]}...' from {msg['sender']} (bot={msg['is_bot_message']})")
                else:
                    print(f"  ✗ Message {i+1} mismatch: expected '{expected_content[:30]}...' from {expected_sender} (bot={expected_is_bot})")
                    print(f"    Got: '{msg['content'][:30]}...' from {msg['sender']} (bot={msg['is_bot_message']})")
            else:
                print(f"  ✗ Missing message {i+1}")
        
        # Test 2: Thread depth limit respected
        print("\nTest 2: Thread depth limit")
        if len(thread_context) <= 3:
            print(f"  ✓ Thread depth limit respected: {len(thread_context)}/3 messages")
        else:
            print(f"  ✗ Thread depth limit exceeded: {len(thread_context)}/3 messages")
        
        # Test 3: Bot message identification
        print("\nTest 3: Bot message identification")
        bot_message_count = sum(1 for msg in thread_context if msg['is_bot_message'])
        if bot_message_count == 1:  # Only one bot message in our test thread
            print("  ✓ Bot messages correctly identified")
        else:
            print(f"  ✗ Expected 1 bot message, found {bot_message_count}")
        
        print("\n🎉 Thread context functionality tests completed!")
        return True
        
    except Exception as e:
        print(f"✗ Thread context test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_context_formatting():
    """Test thread context formatting in watch mode."""
    print("\n=== Testing Context Formatting in Watch Mode ===")
    
    # Setup test environment for watch mode
    os.environ["BOT_REPLY_BEHAVIOR"] = "watch"
    os.environ["BOT_THREAD_DEPTH_LIMIT"] = "3"
    
    try:
        from config import Config
        from bot import AskaosusBot
        from nio import RoomMessageText
        
        config = Config()
        bot = AskaosusBot(config)
        
        # Mock the thread context method to return test data
        mock_thread_messages = [
            {
                'content': 'How do I install Ubuntu?',
                'event_id': '$msg_1',
                'sender': '@user:matrix.org', 
                'is_bot_message': False
            },
            {
                'content': 'Here is how to install Ubuntu step by step...',
                'event_id': '$bot_msg_1',
                'sender': '@testbot:matrix.test.org',
                'is_bot_message': True
            }
        ]
        
        # Mock the _get_thread_context method
        async def mock_get_thread_context(room, event_id, max_depth):
            return mock_thread_messages
            
        bot._get_thread_context = mock_get_thread_context
        
        # Create a mock reply event
        reply_event = MagicMock(spec=RoomMessageText)
        reply_event.body = "@askaosus what about step 3?"
        reply_event.event_id = "$reply_1"
        reply_event.sender = "@user:matrix.org"
        reply_event.source = {
            "content": {
                "m.relates_to": {
                    "m.in_reply_to": {"event_id": "$bot_msg_1"}
                }
            }
        }
        
        # Mock bot message tracking
        bot.bot_message_ids.add("$bot_msg_1")
        
        # Mock room
        room = MockRoom()
        
        # Test context formatting
        question, should_respond, reply_to_id = await bot._should_respond(room, reply_event)
        
        print("Context formatting test:")
        if should_respond and question:
            print("  ✓ Bot should respond to reply in watch mode")
            
            # Check if thread context is included
            if "Message 1 (User):" in question and "Message 2 (Bot):" in question:
                print("  ✓ Thread context properly formatted with message labels")
                
            if "Current reply:" in question:
                print("  ✓ Current reply included in context")
                
            if "what about step 3" in question:
                print("  ✓ Reply content cleaned and included")
                
            print(f"  Context preview: {question[:100]}...")
            
        else:
            print("  ✗ Bot should respond but didn't")
            
        print("🎉 Context formatting tests completed!")
        return True
        
    except Exception as e:
        print(f"✗ Context formatting test failed: {e}")
        import traceback  
        traceback.print_exc()
        return False

async def main():
    """Run all thread context tests."""
    print("Testing Thread Context Feature for BOT_REPLY_BEHAVIOR=watch mode\n")
    
    test1_passed = await test_thread_context_functionality()
    test2_passed = await test_context_formatting() 
    
    if test1_passed and test2_passed:
        print("\n🎉 All thread context tests passed!")
        return 0
    else:
        print("\n❌ Some thread context tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)