#!/usr/bin/env python3
"""
Debug the mention removal logic.
"""

import re

def test_mention_removal():
    """Test different approaches to mention removal."""
    bot_mentions = ["@askaosus", "askaosus"]
    test_messages = [
        "@askaosus How do I install Ubuntu on my laptop?",
        "askaosus please help me",
        "@askaosus can you help?",
        "Hey @askaosus what's up?",
        "I need help from askaosus",
    ]
    
    print("Testing mention removal approaches:")
    
    for msg in test_messages:
        print(f"\nOriginal: '{msg}'")
        
        # Current approach
        result1 = msg
        for mention in bot_mentions:
            result1 = re.sub(rf"\b{re.escape(mention)}\b", "", result1, flags=re.IGNORECASE)
        result1 = result1.strip()
        print(f"Current:  '{result1}'")
        
        # Alternative approach - remove leading/trailing mentions
        result2 = msg.strip()
        for mention in bot_mentions:
            # Remove at start of message
            pattern = rf"^{re.escape(mention)}\s*"
            result2 = re.sub(pattern, "", result2, flags=re.IGNORECASE)
            # Remove at end of message  
            pattern = rf"\s*{re.escape(mention)}$"
            result2 = re.sub(pattern, "", result2, flags=re.IGNORECASE)
            # Remove in middle with word boundaries
            pattern = rf"\s+{re.escape(mention)}\s+"
            result2 = re.sub(pattern, " ", result2, flags=re.IGNORECASE)
        result2 = result2.strip()
        print(f"Improved: '{result2}'")

if __name__ == "__main__":
    test_mention_removal()