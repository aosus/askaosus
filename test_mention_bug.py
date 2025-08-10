#!/usr/bin/env python3
"""
Test the specific bug described in issue #26:
Bot still answers to replies replying to a message with a mention,
even when the reply itself doesn't have a mention.
"""

import os
import sys
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Ensure the src directory is in Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

# Mock the nio module
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

# Mock the nio module
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


async def test_mention_bug_scenario():
    """
    Test the specific bug scenario:
    1. User A sends: "@askaosus how do I install Ubuntu?"
    2. User B replies to User A: "I also need help with this"
    3. Bot should NOT respond to User B's message in 'mention' mode
    """
    print("=== Testing Mention Bug Scenario ===")
    
    # Set up environment for mention mode
    os.environ["MATRIX_HOMESERVER_URL"] = "https://matrix.test.org"
    os.environ["MATRIX_USER_ID"] = "@testbot:matrix.test.org"
    os.environ["MATRIX_PASSWORD"] = "test_password"
    os.environ["LLM_API_KEY"] = "test_key"
    os.environ["BOT_REPLY_BEHAVIOR"] = "mention"
    
    from config import Config
    from bot import AskaosusBot
    
    config = Config()
    bot = AskaosusBot(config)
    bot.start_time = 0  # Process all messages
    
    room = MockMatrixRoom("!test:matrix.org")
    
    # Step 1: Original message from User A with bot mention
    original_message_id = "$original_with_mention"
    original_message = MockRoomMessageText(
        event_id=original_message_id,
        sender="@userA:matrix.org",
        body="@askaosus how do I install Ubuntu?",  # This has the mention
        server_timestamp=1000
    )
    
    # Step 2: User B replies to User A's message WITHOUT mentioning the bot
    # In Matrix, the reply body might include quoted content like:
    # "> @askaosus how do I install Ubuntu?"
    # "I also need help with this"
    
    # This simulates how some Matrix clients format reply messages
    reply_message_body = "> @askaosus how do I install Ubuntu?\n\nI also need help with this"
    
    reply_message = MockRoomMessageText(
        event_id="$reply_without_mention",
        sender="@userB:matrix.org", 
        body=reply_message_body,  # Contains quoted mention but no direct mention
        source={
            'content': {
                'm.relates_to': {
                    'm.in_reply_to': {
                        'event_id': original_message_id
                    }
                }
            }
        },
        server_timestamp=2000
    )
    
    # Mock the original message fetch
    bot.matrix_client.room_get_event.return_value = MockRoomGetEventResponse(original_message)
    
    # Test: Bot should NOT respond because the reply itself doesn't mention the bot
    result = await bot._should_respond(room, reply_message)
    question, should_respond, reply_to_event_id = result
    
    print(f"Original message: {original_message.body}")
    print(f"Reply message: {reply_message.body}")
    print(f"Bot should respond: {should_respond}")
    
    if should_respond:
        print("❌ BUG DETECTED: Bot is responding to reply without direct mention")
        print(f"   Question extracted: {question}")
        return False
    else:
        print("✅ CORRECT: Bot is NOT responding to reply without direct mention")
        return True


async def test_mention_bug_with_formatted_body():
    """
    Test the same scenario but with properly formatted Matrix message
    that separates the quoted content from the actual reply.
    """
    print("\n=== Testing With Proper Matrix Formatted Body ===")
    
    # Set up environment for mention mode  
    os.environ["BOT_REPLY_BEHAVIOR"] = "mention"
    
    from config import Config
    from bot import AskaosusBot
    
    config = Config()
    bot = AskaosusBot(config)
    bot.start_time = 0
    
    room = MockMatrixRoom("!test:matrix.org")
    
    # Original message with mention
    original_message_id = "$original_with_mention_2"
    original_message = MockRoomMessageText(
        event_id=original_message_id,
        sender="@userA:matrix.org",
        body="@askaosus how do I install Ubuntu?",
        server_timestamp=1000
    )
    
    # Reply that has a clean body without quoted content
    # This is what Matrix should provide in the formatted_body or clean body
    reply_message = MockRoomMessageText(
        event_id="$clean_reply",
        sender="@userB:matrix.org",
        body="I also need help with this",  # Clean body without quoted mention
        source={
            'content': {
                'm.relates_to': {
                    'm.in_reply_to': {
                        'event_id': original_message_id
                    }
                }
            }
        },
        server_timestamp=2000
    )
    
    # Mock the original message fetch
    bot.matrix_client.room_get_event.return_value = MockRoomGetEventResponse(original_message)
    
    # Test: Bot should NOT respond
    result = await bot._should_respond(room, reply_message)
    question, should_respond, reply_to_event_id = result
    
    print(f"Original message: {original_message.body}")
    print(f"Reply message (clean): {reply_message.body}")
    print(f"Bot should respond: {should_respond}")
    
    if should_respond:
        print("❌ BUG: Bot is responding when it shouldn't")
        return False
    else:
        print("✅ CORRECT: Bot correctly ignores clean reply without mention")
        return True


async def test_mention_bug_with_direct_mention():
    """
    Test that the bot DOES respond when the reply itself has a mention.
    """
    print("\n=== Testing Reply With Direct Mention ===")
    
    os.environ["BOT_REPLY_BEHAVIOR"] = "mention"
    
    from config import Config
    from bot import AskaosusBot
    
    config = Config()
    bot = AskaosusBot(config)
    bot.start_time = 0
    
    room = MockMatrixRoom("!test:matrix.org")
    
    # Original message
    original_message_id = "$original_3"
    original_message = MockRoomMessageText(
        event_id=original_message_id,
        sender="@userA:matrix.org", 
        body="How do I install Ubuntu?",  # No mention in original
        server_timestamp=1000
    )
    
    # Reply with direct mention
    reply_message = MockRoomMessageText(
        event_id="$reply_with_mention",
        sender="@userB:matrix.org",
        body="@askaosus can you help with this?",  # Direct mention
        source={
            'content': {
                'm.relates_to': {
                    'm.in_reply_to': {
                        'event_id': original_message_id
                    }
                }
            }
        },
        server_timestamp=2000
    )
    
    # Mock the original message fetch
    bot.matrix_client.room_get_event.return_value = MockRoomGetEventResponse(original_message)
    
    # Test: Bot SHOULD respond
    result = await bot._should_respond(room, reply_message)
    question, should_respond, reply_to_event_id = result
    
    print(f"Original message: {original_message.body}")
    print(f"Reply message: {reply_message.body}")
    print(f"Bot should respond: {should_respond}")
    
    if should_respond:
        print("✅ CORRECT: Bot responds to reply with direct mention")
        return True
    else:
        print("❌ ERROR: Bot should respond to direct mention")
        return False


async def main():
    """Run all bug reproduction tests."""
    print("Testing mention bug scenarios...\n")
    
    success = True
    
    # Test the main bug scenario
    if not await test_mention_bug_scenario():
        success = False
    
    # Test with clean formatted body
    if not await test_mention_bug_with_formatted_body():
        success = False
    
    # Test that direct mentions still work
    if not await test_mention_bug_with_direct_mention():
        success = False
    
    if success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))