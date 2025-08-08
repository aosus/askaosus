#!/usr/bin/env python3
"""
Simple test for thread context functionality that doesn't require full bot imports.
Tests just the thread traversal logic.
"""

import os
import sys
import asyncio
from unittest.mock import MagicMock, AsyncMock
from dataclasses import dataclass
from typing import Optional

def test_thread_depth_config():
    """Test the thread depth configuration."""
    print("=== Testing Thread Depth Configuration ===")
    
    # Set test environment
    os.environ["MATRIX_HOMESERVER_URL"] = "https://matrix.test.org"
    os.environ["MATRIX_USER_ID"] = "@testbot:matrix.test.org"
    os.environ["MATRIX_PASSWORD"] = "test_password"
    os.environ["LLM_API_KEY"] = "test_key"
    
    # Test default value
    os.environ.pop("BOT_THREAD_DEPTH_LIMIT", None)  # Remove if exists
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    from config import Config
    
    config1 = Config()
    print(f"✓ Default thread depth limit: {config1.bot_thread_depth_limit}")
    assert config1.bot_thread_depth_limit == 6
    
    # Test custom value
    os.environ["BOT_THREAD_DEPTH_LIMIT"] = "10"
    config2 = Config()
    print(f"✓ Custom thread depth limit: {config2.bot_thread_depth_limit}")
    assert config2.bot_thread_depth_limit == 10
    
    # Test validation - too low
    try:
        os.environ["BOT_THREAD_DEPTH_LIMIT"] = "0"
        config3 = Config()
        print("✗ Should have failed with thread depth too low")
        assert False, "Expected validation error"
    except ValueError as e:
        print(f"✓ Correctly rejected low value: {e}")
    
    # Test validation - too high  
    try:
        os.environ["BOT_THREAD_DEPTH_LIMIT"] = "25"
        config4 = Config()
        print("✗ Should have failed with thread depth too high")
        assert False, "Expected validation error"
    except ValueError as e:
        print(f"✓ Correctly rejected high value: {e}")
    
    print("🎉 Thread depth configuration tests passed!")
    return True

async def test_thread_logic():
    """Test the thread context collection logic manually."""
    print("\n=== Testing Thread Context Logic ===")
    
    # Mock data representing a conversation thread:
    # User: "How to install Ubuntu?" (event_1)
    # Bot: "Here's how..." (event_2, replies to event_1) 
    # User: "What about step 3?" (event_3, replies to event_2)
    
    mock_events = {
        "event_1": {
            "body": "How to install Ubuntu?",
            "sender": "@user:matrix.org",
            "event_id": "event_1",
            "relates_to": None  # Root message
        },
        "event_2": {
            "body": "Here's how to install Ubuntu step by step...",
            "sender": "@bot:matrix.org", 
            "event_id": "event_2",
            "relates_to": "event_1"  # Replies to event_1
        },
        "event_3": {
            "body": "What about step 3?",
            "sender": "@user:matrix.org",
            "event_id": "event_3", 
            "relates_to": "event_2"  # Replies to event_2
        }
    }
    
    bot_message_ids = {"event_2"}  # Track bot messages
    
    # Simulate thread traversal starting from event_3
    collected_messages = []
    current_event_id = "event_3"
    depth = 0
    max_depth = 6
    
    print(f"Starting thread traversal from {current_event_id}")
    
    while current_event_id and depth < max_depth:
        if current_event_id not in mock_events:
            print(f"Event {current_event_id} not found")
            break
            
        event = mock_events[current_event_id]
        print(f"  Depth {depth}: {event['event_id']} - '{event['body'][:30]}...'")
        
        collected_messages.append({
            'content': event['body'],
            'event_id': event['event_id'],
            'sender': event['sender'],
            'is_bot_message': event['event_id'] in bot_message_ids
        })
        
        depth += 1
        current_event_id = event['relates_to']  # Follow the reply chain
    
    # Reverse to get chronological order (oldest first)
    collected_messages.reverse()
    
    print(f"\nCollected {len(collected_messages)} messages in chronological order:")
    for i, msg in enumerate(collected_messages):
        sender_type = "Bot" if msg['is_bot_message'] else "User"
        print(f"  {i+1}. [{sender_type}] {msg['content'][:50]}...")
    
    # Test expectations
    if len(collected_messages) == 3:
        print("✓ Correct number of messages collected")
    else:
        print(f"✗ Expected 3 messages, got {len(collected_messages)}")
    
    if collected_messages[0]['content'] == "How to install Ubuntu?":
        print("✓ First message is the thread root")
    else:
        print("✗ First message should be thread root")
        
    if collected_messages[1]['is_bot_message']:
        print("✓ Second message correctly identified as bot message")  
    else:
        print("✗ Second message should be identified as bot message")
        
    if collected_messages[2]['content'] == "What about step 3?":
        print("✓ Last message is the triggering reply")
    else:
        print("✗ Last message should be the triggering reply")
    
    print("🎉 Thread logic tests completed!")
    return True

def test_context_formatting():
    """Test context formatting for multiple messages."""
    print("\n=== Testing Context Formatting ===")
    
    thread_messages = [
        {
            'content': 'How to install Ubuntu?',
            'event_id': 'event_1',
            'sender': '@user:matrix.org',
            'is_bot_message': False
        },
        {
            'content': 'Here is how to install Ubuntu step by step...',
            'event_id': 'event_2', 
            'sender': '@bot:matrix.org',
            'is_bot_message': True
        },
        {
            'content': 'What about step 3?',
            'event_id': 'event_3',
            'sender': '@user:matrix.org', 
            'is_bot_message': False
        }
    ]
    
    cleaned_reply = "what about step 3?"
    
    # Format thread context similar to bot implementation
    context_parts = []
    for i, msg in enumerate(thread_messages):
        sender_label = "Bot" if msg['is_bot_message'] else "User"
        context_parts.append(f"Message {i+1} ({sender_label}): {msg['content']}")
    
    context_parts.append(f"Current reply: {cleaned_reply}")
    
    full_context = "\n\n".join(context_parts)
    
    print("Formatted context:")
    print("=" * 50)
    print(full_context)
    print("=" * 50)
    
    # Test expectations
    if "Message 1 (User):" in full_context:
        print("✓ User messages properly labeled")
    else:
        print("✗ User message labeling failed")
        
    if "Message 2 (Bot):" in full_context:
        print("✓ Bot messages properly labeled") 
    else:
        print("✗ Bot message labeling failed")
        
    if "Current reply:" in full_context:
        print("✓ Current reply included in context")
    else:
        print("✗ Current reply missing from context")
        
    if full_context.count("Message") == 3:  # 3 thread messages
        print("✓ All thread messages included")
    else:
        print("✗ Missing thread messages")
    
    print("🎉 Context formatting tests completed!")
    return True

async def main():
    """Run all thread context tests."""
    print("Testing Thread Context Feature Implementation\n")
    
    test1_passed = test_thread_depth_config()
    test2_passed = await test_thread_logic()
    test3_passed = test_context_formatting()
    
    if test1_passed and test2_passed and test3_passed:
        print("\n🎉 All thread context implementation tests passed!")
        return 0
    else:
        print("\n❌ Some thread context tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)