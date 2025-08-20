#!/usr/bin/env python3
"""
Test the exact failing cases from edge cases.
"""

def debug_failing_cases():
    """Debug the exact failing cases."""
    
    print("=== Debug Failing Cases ===")
    
    # Case 1: Word boundary issue
    text1 = "Please use askaosusbot for help"
    print(f"Text 1: '{text1}'")
    
    import re
    bot_mentions = ["@askaosus", "askaosus"]
    content_lower = text1.lower()
    
    for mention in bot_mentions:
        mention_lower = mention.lower()
        pattern = rf'\b{re.escape(mention_lower)}\b'
        match = re.search(pattern, content_lower)
        print(f"  Mention: '{mention}', Pattern: '{pattern}', Match: {match}")
        if match:
            print(f"    Matched text: '{match.group()}'")
    
    # Case 2: HTML processing  
    print(f"\nCase 2: HTML processing")
    html_text = "<broken @askaosus <p>help</broken>"
    print(f"HTML: '{html_text}'")
    
    # Try different HTML processing approaches
    approaches = [
        ("Current regex", lambda t: re.sub(r'</?[^>]*>', '', t)),
        ("Non-greedy regex", lambda t: re.sub(r'</?[^>]*?>', '', t)),
        ("Better regex", lambda t: re.sub(r'<[^<>]*>', '', t)),
        ("Iterative removal", lambda t: iterative_html_removal(t)),
    ]
    
    for name, func in approaches:
        try:
            result = func(html_text)
            print(f"  {name}: '{result}'")
            
            # Check for mentions
            content_lower = result.lower()
            mentioned = any(mention.lower() in content_lower for mention in bot_mentions)
            print(f"    Contains mention: {mentioned}")
        except Exception as e:
            print(f"  {name}: Error - {e}")


def iterative_html_removal(html_text):
    """Remove HTML tags iteratively to handle malformed HTML better."""
    import re
    
    text = html_text
    # Keep removing tags until no more are found
    prev_length = len(text)
    while True:
        # Remove well-formed tags first
        text = re.sub(r'<[^<>]*>', '', text)
        # Handle broken tags by removing < and > with content between
        text = re.sub(r'<[^>]*$', '', text)  # Remove incomplete tag at end
        text = re.sub(r'^[^<]*>', '', text)  # Remove incomplete tag at start
        
        if len(text) == prev_length:
            break  # No more changes
        prev_length = len(text)
    
    return text.strip()


if __name__ == "__main__":
    debug_failing_cases()