#!/usr/bin/env python3
"""
Integration test for BOT_REPLY_BEHAVIOR functionality.

This test creates mock Matrix events and tests the bot's reply behavior
under different configurations without needing a real Matrix connection.
"""

import os
import sys
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure the src directory is in Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Mock the nio module since we don't want to connect to Matrix
class MockRoomMessageText:
    def __init__(self, event_id, sender, body, source=None, server_timestamp=None):
        self.event_id = event_id
        self.sender = sender
        self.body = body
        self.source = source or {'content': {}}
        self.server_timestamp = server_timestamp


class MockMatrixRoom:
    def __init__(self, room_id):
        self.room_id = room_id


class MockRoomGetEventResponse:
    def __init__(self, event):
        self.event = event


class MockAsyncClient:
    def __init__(self):
        self.user_id = "@testbot:matrix.org"
        self.access_token = "fake_token"
        self.device_id = "fake_device"
        self.room_get_event = AsyncMock()
        self.room_send = AsyncMock()
        self.room_typing = AsyncMock()
        
    async def room_send(self, room_id, message_type, content):
        # Mock response with event_id
        response = MagicMock()
        response.event_id = f"$mock_event_{len(content['body'])}"
        return response


# Mock the nio imports in bot module
sys.modules['nio'] = MagicMock()
import nio
nio.AsyncClient = MockAsyncClient
nio.ClientConfig = MagicMock()
nio.Event = MagicMock()
nio.LoginResponse = MagicMock()
nio.MatrixRoom = MockMatrixRoom
nio.RoomMessageText = MockRoomMessageText
nio.SyncResponse = MagicMock()
nio.RoomGetEventResponse = MockRoomGetEventResponse


async def create_test_bot(reply_behavior="mention"):
    """Create a bot instance for testing."""
    # Set up test environment
    os.environ["MATRIX_HOMESERVER_URL"] = "https://matrix.test.org"
    os.environ["MATRIX_USER_ID"] = "@testbot:matrix.test.org"
    os.environ["MATRIX_PASSWORD"] = "test_password"
    os.environ["LLM_API_KEY"] = "test_key"
    os.environ["BOT_REPLY_BEHAVIOR"] = reply_behavior
    
    # Import modules after setting environment
    from config import Config
    from bot import AskaosusBot
    
    config = Config()
    bot = AskaosusBot(config)
    
    # Mock the LLM client to avoid API calls
    bot.llm_client = MagicMock()
    bot.llm_client.process_question_with_tools = AsyncMock(return_value="Mock response")
    
    # Set a fake start time to process all messages
    bot.start_time = 0
    
    return bot, config


async def test_reply_behavior_ignore():
    """Test 'ignore' reply behavior."""
    print("\n=== Testing 'ignore' Reply Behavior ===")
    
    bot, config = await create_test_bot("ignore")
    
    # Add a bot message ID to simulate bot messages
    bot_message_id = "$bot_message_123"
    bot.bot_message_ids.add(bot_message_id)
    
    room = MockMatrixRoom("!test:matrix.org")
    
    # Create a reply to bot message WITH mention
    reply_event = MockRoomMessageText(
        event_id="$reply_123",
        sender="@user:matrix.org", 
        body="@askaosus please help",
        source={
            'content': {
                'm.relates_to': {
                    'm.in_reply_to': {
                        'event_id': bot_message_id
                    }
                }
            }
        }
    )
    
    # Mock the original message fetch
    original_message = MockRoomMessageText("$bot_message_123", "@testbot:matrix.test.org", "I can help with that.")
    bot.matrix_client.room_get_event.return_value = MockRoomGetEventResponse(original_message)
    
    # Test that the bot ignores the reply even with mention
    result = await bot._should_respond(room, reply_event)
    question, should_respond, reply_to_event_id = result
    
    if should_respond:
        print("✗ Bot should ignore reply to bot message in 'ignore' mode")
        return False
    else:
        print("✓ Bot correctly ignored reply to bot message in 'ignore' mode")
    
    # Test direct mention (should still work)
    direct_mention = MockRoomMessageText(
        event_id="$direct_123",
        sender="@user:matrix.org",
        body="@askaosus how to install Ubuntu?"
    )
    
    result = await bot._should_respond(room, direct_mention)
    question, should_respond, reply_to_event_id = result
    
    if should_respond and question:
        print("✓ Bot still responds to direct mentions in 'ignore' mode")
        print(f"   Question: {question}")
        return True
    else:
        print("✗ Bot should still respond to direct mentions in 'ignore' mode")
        return False


async def test_reply_behavior_mention():
    """Test 'mention' reply behavior."""
    print("\n=== Testing 'mention' Reply Behavior ===")
    
    bot, config = await create_test_bot("mention")
    
    # Add a bot message ID to simulate bot messages
    bot_message_id = "$bot_message_123"
    bot.bot_message_ids.add(bot_message_id)
    
    room = MockMatrixRoom("!test:matrix.org")
    
    # Mock the original message fetch
    original_message = MockRoomMessageText("$bot_message_123", "@testbot:matrix.test.org", "I can help with that.")
    bot.matrix_client.room_get_event.return_value = MockRoomGetEventResponse(original_message)
    
    # Test reply to bot message WITHOUT mention (should be ignored)
    reply_without_mention = MockRoomMessageText(
        event_id="$reply_no_mention",
        sender="@user:matrix.org",
        body="thanks for the help!",
        source={
            'content': {
                'm.relates_to': {
                    'm.in_reply_to': {
                        'event_id': bot_message_id
                    }
                }
            }
        }
    )
    
    result = await bot._should_respond(room, reply_without_mention)
    question, should_respond, reply_to_event_id = result
    
    if should_respond:
        print("✗ Bot should ignore reply to bot message without mention in 'mention' mode")
        return False
    else:
        print("✓ Bot correctly ignored reply to bot message without mention")
    
    # Test reply to bot message WITH mention (should respond)
    reply_with_mention = MockRoomMessageText(
        event_id="$reply_with_mention",
        sender="@user:matrix.org",
        body="@askaosus can you explain more?",
        source={
            'content': {
                'm.relates_to': {
                    'm.in_reply_to': {
                        'event_id': bot_message_id
                    }
                }
            }
        }
    )
    
    result = await bot._should_respond(room, reply_with_mention)
    question, should_respond, reply_to_event_id = result
    
    if should_respond and question:
        print("✓ Bot responds to reply to bot message with mention")
        print(f"   Question context: {question[:100]}...")
        
        # Verify the question was cleaned properly
        if "@askaosus" not in question:
            print("✓ Bot mention was cleaned from question")
            return True
        else:
            print("✗ Bot mention was not cleaned from question")
            return False
    else:
        print("✗ Bot should respond to reply to bot message with mention in 'mention' mode")
        return False


async def test_reply_behavior_watch():
    """Test 'watch' reply behavior."""
    print("\n=== Testing 'watch' Reply Behavior ===")
    
    bot, config = await create_test_bot("watch")
    
    # Add a bot message ID to simulate bot messages
    bot_message_id = "$bot_message_123"
    bot.bot_message_ids.add(bot_message_id)
    
    room = MockMatrixRoom("!test:matrix.org")
    
    # Mock the original message fetch
    original_message = MockRoomMessageText("$bot_message_123", "@testbot:matrix.test.org", "I can help with that.")
    bot.matrix_client.room_get_event.return_value = MockRoomGetEventResponse(original_message)
    
    # Test reply to bot message WITHOUT mention (should respond in watch mode)
    reply_without_mention = MockRoomMessageText(
        event_id="$reply_no_mention",
        sender="@user:matrix.org",
        body="can you provide more details?",
        source={
            'content': {
                'm.relates_to': {
                    'm.in_reply_to': {
                        'event_id': bot_message_id
                    }
                }
            }
        }
    )
    
    result = await bot._should_respond(room, reply_without_mention)
    question, should_respond, reply_to_event_id = result
    
    if should_respond and question:
        print("✓ Bot responds to reply to bot message without mention in 'watch' mode")
        print(f"   Question context: {question[:100]}...")
    else:
        print("✗ Bot should respond to reply to bot message without mention in 'watch' mode")
        return False
    
    # Test reply to bot message WITH mention (should also respond)
    reply_with_mention = MockRoomMessageText(
        event_id="$reply_with_mention",
        sender="@user:matrix.org", 
        body="@askaosus please elaborate",
        source={
            'content': {
                'm.relates_to': {
                    'm.in_reply_to': {
                        'event_id': bot_message_id
                    }
                }
            }
        }
    )
    
    result = await bot._should_respond(room, reply_with_mention)
    question, should_respond, reply_to_event_id = result
    
    if should_respond and question:
        print("✓ Bot also responds to reply to bot message with mention in 'watch' mode")
        
        # Verify content was cleaned  
        if "@askaosus" not in question:
            print("✓ Bot mention was cleaned from question")
            return True
        else:
            print("✗ Bot mention was not cleaned from question")
            return False
    else:
        print("✗ Bot should also respond to reply to bot message with mention in 'watch' mode")
        return False


async def test_reply_to_non_bot_messages():
    """Test replies to non-bot messages."""
    print("\n=== Testing Replies to Non-Bot Messages ===")
    
    bot, config = await create_test_bot("watch")  # Use watch mode to be most permissive
    
    room = MockMatrixRoom("!test:matrix.org")
    
    # Create a non-bot message (not in bot.bot_message_ids)
    non_bot_message_id = "$user_message_456"
    
    # Mock the original message fetch (from another user)
    original_message = MockRoomMessageText("$user_message_456", "@otheruser:matrix.org", "How do I install Ubuntu?")
    bot.matrix_client.room_get_event.return_value = MockRoomGetEventResponse(original_message)
    
    # Test reply to non-bot message WITHOUT mention (should be ignored)
    reply_without_mention = MockRoomMessageText(
        event_id="$reply_to_user",
        sender="@user:matrix.org",
        body="I had the same question",
        source={
            'content': {
                'm.relates_to': {
                    'm.in_reply_to': {
                        'event_id': non_bot_message_id
                    }
                }
            }
        }
    )
    
    result = await bot._should_respond(room, reply_without_mention)
    question, should_respond, reply_to_event_id = result
    
    if should_respond:
        print("✗ Bot should ignore reply to non-bot message without mention")
        return False
    else:
        print("✓ Bot correctly ignored reply to non-bot message without mention")
    
    # Test reply to non-bot message WITH mention (should respond with context)
    reply_with_mention = MockRoomMessageText(
        event_id="$reply_to_user_mention",
        sender="@user:matrix.org",
        body="@askaosus can you help with this?",
        source={
            'content': {
                'm.relates_to': {
                    'm.in_reply_to': {
                        'event_id': non_bot_message_id
                    }
                }
            }
        }
    )
    
    result = await bot._should_respond(room, reply_with_mention)
    question, should_respond, reply_to_event_id = result
    
    if should_respond and question:
        print("✓ Bot responds to reply to non-bot message with mention")
        print(f"   Question context: {question[:100]}...")
        
        # Verify context includes original message
        if "How do I install Ubuntu?" in question:
            print("✓ Original message context included")
            return True
        else:
            print("✗ Original message context not included")
            return False
    else:
        print("✗ Bot should respond to reply to non-bot message with mention")
        return False


async def test_message_reply_tracking():
    """Test that bot tracks its own message IDs for reply behavior."""
    print("\n=== Testing Message Reply Tracking ===")
    
    bot, config = await create_test_bot("watch")
    
    room = MockMatrixRoom("!test:matrix.org")
    
    # Mock a successful room_send response
    mock_response = MagicMock()
    mock_response.event_id = "$bot_sent_message_789"
    bot.matrix_client.room_send.return_value = mock_response
    
    # Create a direct mention to trigger a response
    direct_mention = MockRoomMessageText(
        event_id="$user_message",
        sender="@user:matrix.org",
        body="@askaosus help me please"
    )
    
    # Mock the message processing to avoid calling LLM
    original_process = bot._process_question
    bot._process_question = AsyncMock(return_value="I can help you!")
    
    try:
        # Process the message through the full callback
        await bot.message_callback(room, direct_mention)
        
        # Check that the bot's message ID was tracked
        if "$bot_sent_message_789" in bot.bot_message_ids:
            print("✓ Bot message ID correctly tracked")
            
            # Verify room_send was called with reply information
            bot.matrix_client.room_send.assert_called_once()
            call_args = bot.matrix_client.room_send.call_args
            content = call_args.kwargs['content']
            
            # Check if reply structure is present (it should reply to user's message)
            if 'm.relates_to' in content and 'm.in_reply_to' in content['m.relates_to']:
                reply_to_id = content['m.relates_to']['m.in_reply_to']['event_id']
                if reply_to_id == "$user_message":
                    print("✓ Bot response includes correct reply structure")
                    return True
                else:
                    print(f"✗ Bot replied to wrong message: {reply_to_id}")
                    return False
            else:
                print("✓ Bot response sent (no reply structure needed for direct mention)")
                return True
                
        else:
            print("✗ Bot message ID was not tracked")
            return False
            
    except Exception as e:
        print(f"✗ Error during message processing: {e}")
        return False
    finally:
        # Restore original method
        bot._process_question = original_process


async def run_integration_tests():
    """Run all integration tests."""
    print("Running integration tests for BOT_REPLY_BEHAVIOR...")
    
    tests = [
        test_reply_behavior_ignore,
        test_reply_behavior_mention,  
        test_reply_behavior_watch,
        test_reply_to_non_bot_messages,
        test_message_reply_tracking,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            # Clean environment for each test
            for key in ["BOT_REPLY_BEHAVIOR"]:
                if key in os.environ:
                    del os.environ[key]
                    
            if await test():
                passed += 1
                print(f"✓ {test.__name__} PASSED")
            else:
                failed += 1 
                print(f"✗ {test.__name__} FAILED")
                
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__} ERROR: {e}")
    
    print(f"\n=== Integration Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    if failed == 0:
        print("🎉 All integration tests passed!")
        return True
    else:
        print("❌ Some integration tests failed!")
        return False


def main():
    """Main test runner."""
    try:
        success = asyncio.run(run_integration_tests())
        return 0 if success else 1
    except Exception as e:
        print(f"Fatal error running tests: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())