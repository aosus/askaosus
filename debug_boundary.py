#!/usr/bin/env python3
"""
Debug the word boundary issues.
"""

import re

def test_word_boundary():
    """Test word boundary logic."""
    
    bot_mentions = ["@askaosus", "askaosus"]
    test_texts = [
        "askaosus help",  # Should match
        "askaosusbot help",  # Should NOT match  
        "help askaosus please",  # Should match
        "Please ask aosus-bot",  # Should NOT match
    ]
    
    for text in test_texts:
        print(f"\nTesting: '{text}'")
        content_lower = text.lower()
        
        # Current logic
        mentioned = False
        for mention in bot_mentions:
            mention_lower = mention.lower()
            if mention.startswith('@'):
                pattern = rf'\b{re.escape(mention_lower)}\b'
                if re.search(pattern, content_lower):
                    mentioned = True
                    print(f"  Found mention: '{mention}' with pattern: '{pattern}'")
                    break
            else:
                pattern = rf'\b{re.escape(mention_lower)}\b'
                if re.search(pattern, content_lower):
                    mentioned = True
                    print(f"  Found mention: '{mention}' with pattern: '{pattern}'")
                    break
        
        print(f"  Result: {mentioned}")


def test_html_processing():
    """Test HTML processing."""
    
    test_html = "<broken @askaosus <p>help</broken>"
    
    print(f"Original: {test_html}")
    
    # Process with current logic
    import html
    
    # Handle <br> tags first
    processed = re.sub(r'<br\s*/?>', '\n', test_html, flags=re.IGNORECASE)
    print(f"After <br> handling: {processed}")
    
    # Remove HTML tags
    processed = re.sub(r'</?[^>]*>', '', processed)
    print(f"After tag removal: {processed}")
    
    # Decode HTML entities
    processed = html.unescape(processed).strip()
    print(f"After entity decoding: {processed}")
    
    # Check for mention
    content_lower = processed.lower()
    mentioned = False
    for mention in ["@askaosus", "askaosus"]:
        mention_lower = mention.lower()
        pattern = rf'\b{re.escape(mention_lower)}\b'
        if re.search(pattern, content_lower):
            mentioned = True
            print(f"Found mention: '{mention}' with pattern: '{pattern}'")
            break
    
    print(f"Final result: {mentioned}")


if __name__ == "__main__":
    print("=== Testing Word Boundaries ===")
    test_word_boundary()
    
    print("\n\n=== Testing HTML Processing ===")
    test_html_processing()