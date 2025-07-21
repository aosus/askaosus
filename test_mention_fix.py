#!/usr/bin/env python3
"""
Test the improved mention removal logic.
"""

import re

def test_improved_mention_removal():
    """Test the new mention removal approach."""
    bot_mentions = ["@askaosus", "askaosus"]
    test_messages = [
        "@askaosus How do I install Ubuntu on my laptop?",
        "askaosus please help me",
        "@askaosus can you help?",
        "Hey @askaosus what's up?",
        "I need help from askaosus",
    ]
    
    print("Testing improved mention removal:")
    
    for message_body in test_messages:
        print(f"\nOriginal: '{message_body}'")
        
        # New improved approach
        question = message_body
        for mention in bot_mentions:
            # Remove mentions more comprehensively
            patterns = [
                rf"\b{re.escape(mention)}\b",  # Exact mention
                rf"@{re.escape(mention.lstrip('@'))}\b",  # @mention variant
                rf"\b{re.escape(mention.lstrip('@'))}\b",  # mention without @
            ]
            for pattern in patterns:
                question = re.sub(pattern, "", question, flags=re.IGNORECASE)
        question = re.sub(r'\s+', ' ', question).strip()  # Clean up extra spaces
        
        print(f"Result:   '{question}'")

if __name__ == "__main__":
    test_improved_mention_removal()