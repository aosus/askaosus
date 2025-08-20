#!/usr/bin/env python3
"""
Direct test of the mention detection bug without full bot setup.
"""

import os
import sys
import re

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_mention_detection_in_quoted_content():
    """Test if the current mention detection logic has the bug."""
    
    print("=== Testing Mention Detection Logic ===")
    
    # Bot mentions configuration
    bot_mentions = ["@askaosus", "askaosus"]
    
    # Test cases that should trigger the bug
    test_cases = [
        {
            "name": "Reply with quoted mention",
            "message_body": "> @askaosus how do I install Ubuntu?\n\nI also need help with this",
            "should_be_mentioned": False,  # Reply itself has no mention
            "description": "Reply includes quoted content with mention, but reply itself has no mention"
        },
        {
            "name": "Reply with direct mention",
            "message_body": "@askaosus can you help me?",
            "should_be_mentioned": True,  # Reply has direct mention
            "description": "Direct mention should be detected"
        },
        {
            "name": "Clean reply without mention",
            "message_body": "I also need help with this",
            "should_be_mentioned": False,  # No mention at all
            "description": "Clean reply without any mention"
        },
        {
            "name": "Multiple quoted lines with mention",
            "message_body": "> @user: Original question\n> @askaosus please help\n\nWhat about this issue?",
            "should_be_mentioned": False,  # Only quoted content has mention
            "description": "Multiple quoted lines, mention only in quoted part"
        }
    ]
    
    # Current logic from bot.py (lines 370-373)
    def current_mention_detection(message_body, bot_mentions):
        """Current mention detection logic from the bot."""
        message_lower = message_body.lower()
        mentioned = any(mention.lower() in message_lower for mention in bot_mentions)
        return mentioned
    
    # Test each case
    print(f"Bot mentions: {bot_mentions}\n")
    
    bug_detected = False
    for test_case in test_cases:
        detected = current_mention_detection(test_case["message_body"], bot_mentions)
        expected = test_case["should_be_mentioned"]
        
        print(f"Test: {test_case['name']}")
        print(f"Message: {repr(test_case['message_body'])}")
        print(f"Expected mentioned: {expected}")
        print(f"Actually detected: {detected}")
        
        if detected == expected:
            print("✅ CORRECT")
        else:
            print("❌ BUG DETECTED!")
            bug_detected = True
            
        print(f"Description: {test_case['description']}")
        print("-" * 50)
    
    if bug_detected:
        print("\n🐛 BUG CONFIRMED: Current logic detects mentions in quoted content")
        return True
    else:
        print("\n✅ No bug detected with current logic")
        return False


def test_improved_mention_detection():
    """Test improved mention detection that excludes quoted content."""
    
    print("\n=== Testing Improved Mention Detection ===")
    
    bot_mentions = ["@askaosus", "askaosus"]
    
    def improved_mention_detection(message_body, bot_mentions):
        """Improved logic that excludes quoted lines."""
        # Remove quoted lines (lines starting with "> ")
        lines = message_body.split('\n')
        non_quote_lines = []
        for line in lines:
            if not line.strip().startswith('> '):
                non_quote_lines.append(line)
        
        cleaned_body = '\n'.join(non_quote_lines).strip()
        
        # Now check for mentions in the cleaned content
        cleaned_lower = cleaned_body.lower()
        mentioned = any(mention.lower() in cleaned_lower for mention in bot_mentions)
        return mentioned
    
    # Test the same cases
    test_cases = [
        {
            "name": "Reply with quoted mention",
            "message_body": "> @askaosus how do I install Ubuntu?\n\nI also need help with this",
            "should_be_mentioned": False,
        },
        {
            "name": "Reply with direct mention", 
            "message_body": "@askaosus can you help me?",
            "should_be_mentioned": True,
        },
        {
            "name": "Clean reply without mention",
            "message_body": "I also need help with this",
            "should_be_mentioned": False,
        },
        {
            "name": "Multiple quoted lines with mention",
            "message_body": "> @user: Original question\n> @askaosus please help\n\nWhat about this issue?",
            "should_be_mentioned": False,
        },
        {
            "name": "Quote with mention AND direct mention",
            "message_body": "> @askaosus original question\n\n@askaosus can you also help with this?",
            "should_be_mentioned": True,  # Has direct mention in non-quoted part
        }
    ]
    
    print(f"Bot mentions: {bot_mentions}\n")
    
    all_correct = True
    for test_case in test_cases:
        detected = improved_mention_detection(test_case["message_body"], bot_mentions)
        expected = test_case["should_be_mentioned"]
        
        print(f"Test: {test_case['name']}")
        print(f"Message: {repr(test_case['message_body'])}")
        print(f"Expected: {expected}, Detected: {detected}")
        
        if detected == expected:
            print("✅ CORRECT")
        else:
            print("❌ FAILED!")
            all_correct = False
            
        print("-" * 40)
    
    if all_correct:
        print("\n🎉 Improved logic works correctly!")
        return True
    else:
        print("\n❌ Improved logic has issues")
        return False


def main():
    """Run the mention detection tests."""
    print("Testing mention detection logic for quoted content bug...\n")
    
    # Test if current logic has the bug
    has_bug = test_mention_detection_in_quoted_content()
    
    # Test improved logic
    improved_works = test_improved_mention_detection()
    
    if has_bug and improved_works:
        print("\n🎯 CONCLUSION: Bug confirmed and fix validated!")
        return 0
    elif not has_bug:
        print("\n🤔 CONCLUSION: No bug detected with current logic")
        return 1
    else:
        print("\n❌ CONCLUSION: Bug detected but fix doesn't work")
        return 1


if __name__ == "__main__":
    sys.exit(main())