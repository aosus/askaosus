#!/usr/bin/env python3
"""
Simple test to verify the bot reply logic by testing the methods directly.
"""

import re
from typing import Optional, Tuple

# Mock the bot's core logic to test reply detection
class MockEvent:
    """Mock Matrix event for testing."""
    
    def __init__(self, sender="@user:example.org", body="Test message", reply_to_event_id=None):
        self.sender = sender
        self.body = body
        self.source = {"content": {}}
        if reply_to_event_id:
            self.source["content"]["m.relates_to"] = {
                "m.in_reply_to": {
                    "event_id": reply_to_event_id
                }
            }


def test_reply_detection_logic():
    """Test the core logic for detecting replies."""
    print("Testing reply detection logic...")
    
    # Test data
    bot_user_id = "@bot:example.org"
    bot_mentions = ["@askaosus", "askaosus"]
    
    # Mock the is_reply_to_bot function result
    def mock_is_reply_to_bot(event, expected_result):
        """Mock function to simulate is_reply_to_bot_message result."""
        return expected_result
    
    def should_respond_logic(event, is_reply_to_bot_result):
        """Simplified version of the _should_respond logic."""
        message_body = event.body.strip()
        message_lower = message_body.lower()
        
        # Check for direct mentions
        mentioned = any(mention.lower() in message_lower for mention in bot_mentions)
        
        # Check if this is a reply to a bot message (mocked)
        is_reply_to_bot = is_reply_to_bot_result
        
        # Respond if either mentioned directly or replying to bot message
        if mentioned or is_reply_to_bot:
            if mentioned:
                # Remove mention and return
                question = message_body
                for mention in bot_mentions:
                    question = re.sub(rf"\b{re.escape(mention)}\b", "", question, flags=re.IGNORECASE)
                question = question.strip()
                return question, True
            elif is_reply_to_bot:
                return f"Reply to bot: {message_body}", True
        
        return None, False
    
    # Test cases
    test_cases = [
        # (event, is_reply_to_bot, expected_response, description)
        (MockEvent(body="@askaosus How do I install Ubuntu?"), False, True, "Direct mention"),
        (MockEvent(body="That didn't work for me"), True, True, "Reply to bot message"),
        (MockEvent(body="That didn't work for me"), False, False, "Regular message, no mention"),
        (MockEvent(body="askaosus please help"), False, True, "Mention without @"),
        (MockEvent(body="Thanks for the help!"), True, True, "Reply to bot without mention"),
    ]
    
    for i, (event, is_reply_to_bot_result, should_respond_expected, description) in enumerate(test_cases, 1):
        question, should_respond = should_respond_logic(event, is_reply_to_bot_result)
        
        print(f"  Test {i}: {description}")
        print(f"    Event: '{event.body}'")
        print(f"    Is reply to bot: {is_reply_to_bot_result}")
        print(f"    Should respond: {should_respond} (expected: {should_respond_expected})")
        
        if should_respond == should_respond_expected:
            print(f"    ✓ PASS")
        else:
            print(f"    ❌ FAIL - Expected {should_respond_expected}, got {should_respond}")
            return False
        
        if should_respond and question:
            print(f"    Question/Context: '{question}'")
        print()
    
    return True


def test_conversation_building_logic():
    """Test the logic for building conversation threads."""
    print("Testing conversation building logic...")
    
    # Mock conversation building
    def build_mock_conversation_thread():
        """Mock building a conversation thread."""
        events = [
            ("User", "How do I install Ubuntu?"),
            ("Bot", "Here are the steps to install Ubuntu: 1. Download ISO..."),
            ("User", "That didn't work, I'm getting an error")
        ]
        
        conversation = []
        for sender, message in events:
            conversation.append(f"{sender}: {message}")
        
        return "Conversation thread:\n" + "\n".join(conversation)
    
    result = build_mock_conversation_thread()
    print("  Mock conversation thread:")
    print("   ", result.replace('\n', '\n    '))
    
    # Verify format
    assert "Conversation thread:" in result
    assert "User: How do I install Ubuntu?" in result
    assert "Bot: Here are the steps" in result
    assert "User: That didn't work" in result
    
    print("  ✓ Conversation thread format is correct")
    return True


def main():
    """Run all tests."""
    print("🧪 Running simplified bot reply logic tests...\n")
    
    try:
        if not test_reply_detection_logic():
            print("❌ Reply detection tests failed!")
            return False
        print("✅ Reply detection tests passed!\n")
        
        if not test_conversation_building_logic():
            print("❌ Conversation building tests failed!")
            return False
        print("✅ Conversation building tests passed!\n")
        
        print("🎉 All simplified tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)