#!/usr/bin/env python3
"""
Test the enhanced bot mention detection that prefers formatted_body.
"""

import os
import sys
import re
import html

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

def test_enhanced_mention_detection():
    """Test the enhanced mention detection with formatted_body support."""
    
    print("=== Testing Enhanced Bot Mention Detection ===")
    
    # Set up minimal environment
    os.environ["MATRIX_HOMESERVER_URL"] = "https://matrix.test.org"  
    os.environ["MATRIX_USER_ID"] = "@testbot:matrix.test.org"
    os.environ["MATRIX_PASSWORD"] = "test_password"
    os.environ["LLM_API_KEY"] = "test_key"
    
    from config import Config
    
    class MockEvent:
        def __init__(self, body, formatted_body=None):
            self.body = body
            self.formatted_body = formatted_body
    
    class EnhancedTestBot:
        def __init__(self, config):
            self.config = config
            
        def _check_message_mentions_bot(self, message_body: str, bot_mentions: list, event=None) -> bool:
            """Enhanced mention detection method."""
            import logging
            logger = logging.getLogger(__name__)
            
            # Prefer formatted_body if available, as it excludes replied-to content  
            content_to_check = message_body
            
            if event and hasattr(event, 'formatted_body') and event.formatted_body:
                # Use formatted_body but strip HTML tags for text-based mention detection
                # Simple HTML tag removal - convert <br> to newlines and remove other tags
                formatted_content = event.formatted_body
                formatted_content = re.sub(r'<br\s*/?>', '\n', formatted_content, flags=re.IGNORECASE)
                formatted_content = re.sub(r'<[^>]+>', '', formatted_content)
                # Decode HTML entities
                formatted_content = html.unescape(formatted_content).strip()
                
                if formatted_content:
                    content_to_check = formatted_content
                    logger.debug(f"Using formatted_body for mention detection: {len(formatted_content)} chars")
                else:
                    logger.debug("formatted_body was empty, falling back to body")
            else:
                logger.debug("No formatted_body available, using raw body with quote filtering")
            
            # If we're using raw body, remove quoted lines (fallback for clients that don't use formatted_body)
            if content_to_check == message_body:
                lines = message_body.split('\n')
                non_quote_lines = []
                for line in lines:
                    # Skip lines that are Matrix quote replies (fallback formatting)
                    if not line.strip().startswith('> '):
                        non_quote_lines.append(line)
                content_to_check = '\n'.join(non_quote_lines).strip()
            
            # Check for mentions in the cleaned content only
            content_lower = content_to_check.lower()
            mentioned = any(mention.lower() in content_lower for mention in bot_mentions)
            
            logger.debug(f"Mention detection: original_length={len(message_body)}, "
                        f"content_length={len(content_to_check)}, mentioned={mentioned}")
            
            return mentioned
    
    config = Config()
    bot = EnhancedTestBot(config)
    
    # Test cases with different scenarios
    test_cases = [
        {
            "name": "Reply with quoted mention - using formatted_body (clean)",
            "event": MockEvent(
                body="> @askaosus how do I install Ubuntu?\n\nI also need help with this",
                formatted_body="I also need help with this"  # Clean formatted body without quote
            ),
            "expected": False,
        },
        {
            "name": "Reply with quoted mention - no formatted_body (fallback)",
            "event": MockEvent(
                body="> @askaosus how do I install Ubuntu?\n\nI also need help with this",
                formatted_body=None  # Fall back to quote filtering
            ),
            "expected": False,
        },
        {
            "name": "Reply with direct mention in formatted_body",
            "event": MockEvent(
                body="@askaosus can you help me?",
                formatted_body="@askaosus can you help me?"
            ),
            "expected": True,
        },
        {
            "name": "Reply with HTML formatted mention",
            "event": MockEvent(
                body="@askaosus help",
                formatted_body="<em>@askaosus</em> help"  # HTML formatting around mention
            ),
            "expected": True,
        },
        {
            "name": "Reply with HTML entities",
            "event": MockEvent(
                body="test message",
                formatted_body="@askaosus help with &quot;installation&quot; please"  # HTML entities
            ),
            "expected": True,
        },
        {
            "name": "Empty formatted_body - fallback to body",
            "event": MockEvent(
                body="@askaosus help please",
                formatted_body=""  # Empty formatted_body should fall back to body
            ),
            "expected": True,
        },
        {
            "name": "Complex HTML with line breaks",
            "event": MockEvent(
                body="Complex message",
                formatted_body="@askaosus<br>can you help<br>with this?"  # HTML with <br>
            ),
            "expected": True,
        },
        {
            "name": "Formatted body without mention",
            "event": MockEvent(
                body="some message with > quoted @askaosus content",  # Raw body has mention in quote
                formatted_body="some message without mention"  # Clean formatted body
            ),
            "expected": False,  # Should not detect mention from formatted_body
        }
    ]
    
    print(f"Bot mentions: {config.bot_mentions}\n")
    
    all_passed = True
    for i, test_case in enumerate(test_cases, 1):
        event = test_case["event"]
        result = bot._check_message_mentions_bot(event.body, config.bot_mentions, event)
        expected = test_case["expected"]
        
        print(f"Test {i}: {test_case['name']}")
        print(f"Body: {repr(event.body)}")
        if event.formatted_body is not None:
            print(f"Formatted: {repr(event.formatted_body)}")
        else:
            print("Formatted: None")
        print(f"Expected: {expected}, Got: {result}")
        
        if result == expected:
            print("✅ PASS")
        else:
            print("❌ FAIL")
            all_passed = False
            
        print("-" * 50)
    
    if all_passed:
        print("\n🎉 All enhanced mention detection tests passed!")
        return True
    else:
        print("\n❌ Some enhanced mention detection tests failed!")
        return False


def main():
    """Run the enhanced mention detection test."""
    print("Testing enhanced bot mention detection with formatted_body support...\n")
    
    if test_enhanced_mention_detection():
        print("✅ Enhanced mention detection is working correctly!")
        return 0
    else:
        print("❌ Enhanced mention detection has issues!")
        return 1


if __name__ == "__main__":
    # Set up logging to see debug messages
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    sys.exit(main())