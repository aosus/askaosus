#!/usr/bin/env python3
"""
Test edge cases for the mention detection fix.
"""

import os
import sys

# Add src to path  
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

def test_edge_cases():
    """Test edge cases for mention detection."""
    
    print("=== Testing Edge Cases ===")
    
    # Set up environment
    os.environ["MATRIX_HOMESERVER_URL"] = "https://matrix.test.org"
    os.environ["MATRIX_USER_ID"] = "@testbot:matrix.test.org"  
    os.environ["MATRIX_PASSWORD"] = "test_password"
    os.environ["LLM_API_KEY"] = "test_key"
    
    from config import Config
    
    class MockEvent:
        def __init__(self, body, formatted_body=None):
            self.body = body
            self.formatted_body = formatted_body
    
    class TestBot:
        def __init__(self, config):
            self.config = config
            import logging
            self.logger = logging.getLogger(__name__)
        
        def _check_message_mentions_bot(self, message_body: str, bot_mentions: list, event=None) -> bool:
            import re, html
            logger = self.logger
            
            content_to_check = message_body
            
            if event and hasattr(event, 'formatted_body') and event.formatted_body:
                formatted_content = event.formatted_body
                formatted_content = re.sub(r'<br\s*/?>', '\n', formatted_content, flags=re.IGNORECASE)
                formatted_content = re.sub(r'<[^>]+>', '', formatted_content)
                formatted_content = html.unescape(formatted_content).strip()
                
                if formatted_content:
                    content_to_check = formatted_content
                    logger.debug(f"Using formatted_body for mention detection: {len(formatted_content)} chars")
                else:
                    logger.debug("formatted_body was empty, falling back to body")
            else:
                logger.debug("No formatted_body available, using raw body with quote filtering")
            
            if content_to_check == message_body:
                lines = message_body.split('\n')
                non_quote_lines = []
                for line in lines:
                    if not line.strip().startswith('> '):
                        non_quote_lines.append(line)
                content_to_check = '\n'.join(non_quote_lines).strip()
            
            content_lower = content_to_check.lower()
            mentioned = any(mention.lower() in content_lower for mention in bot_mentions)
            
            return mentioned
    
    config = Config()
    bot = TestBot(config)
    
    # Edge case test scenarios
    edge_cases = [
        {
            "name": "Empty message",
            "event": MockEvent("", ""),
            "expected": False,
        },
        {
            "name": "Only whitespace",
            "event": MockEvent("   \n\t  ", "   \n\t  "),
            "expected": False,
        },
        {
            "name": "Only quoted content",
            "event": MockEvent("> @askaosus help\n> with this issue", None),
            "expected": False,
        },
        {
            "name": "Multiple quote styles", 
            "event": MockEvent("> @askaosus original\n>> nested quote\n> another quote", None),
            "expected": False,
        },
        {
            "name": "Mention at start of quote line",
            "event": MockEvent("> @askaosus\nActual message without mention", None),
            "expected": False,
        },
        {
            "name": "Mention after quote line",
            "event": MockEvent("> some quote\n@askaosus help", None),
            "expected": True,
        },
        {
            "name": "Case variations",
            "event": MockEvent("@ASKAOSUS help", "@ASKAOSUS help"),
            "expected": True,
        },
        {
            "name": "Partial mention (shouldn't match)",
            "event": MockEvent("Please ask aosus-bot for help", "Please ask aosus-bot for help"),
            "expected": False,  # Partial match should not trigger
        },
        {
            "name": "Mention in middle of word (shouldn't match)",
            "event": MockEvent("Please use askaosusbot for help", "Please use askaosusbot for help"),
            "expected": False,  # Word boundary check should prevent this
        },
        {
            "name": "Multiple mentions",
            "event": MockEvent("@askaosus and askaosus please help", "@askaosus and askaosus please help"),
            "expected": True,
        },
        {
            "name": "Very long message with mention at end",
            "event": MockEvent("A" * 1000 + " @askaosus", "A" * 1000 + " @askaosus"),
            "expected": True,
        },
        {
            "name": "Complex HTML with nested tags",
            "event": MockEvent(
                "complex message",
                "<p><strong><em>@askaosus</em></strong> can you <br><code>help</code> please?</p>"
            ),
            "expected": True,
        },
        {
            "name": "HTML entities and special characters",
            "event": MockEvent(
                "test",
                "@askaosus help with &lt;installation&gt; &amp; configuration"
            ),
            "expected": True,
        },
        {
            "name": "Malformed HTML",
            "event": MockEvent(
                "fallback",
                "<broken @askaosus <p>help</broken>"
            ),
            "expected": True,
        }
    ]
    
    print(f"Bot mentions: {config.bot_mentions}\n")
    
    all_passed = True
    for i, test_case in enumerate(edge_cases, 1):
        event = test_case["event"]
        try:
            result = bot._check_message_mentions_bot(event.body, config.bot_mentions, event)
            expected = test_case["expected"]
            
            print(f"Test {i}: {test_case['name']}")
            if len(event.body) > 50:
                print(f"Body: {repr(event.body[:47] + '...')}")
            else:
                print(f"Body: {repr(event.body)}")
            
            if event.formatted_body and len(event.formatted_body) > 50:
                print(f"Formatted: {repr(event.formatted_body[:47] + '...')}")
            elif event.formatted_body:
                print(f"Formatted: {repr(event.formatted_body)}")
            
            print(f"Expected: {expected}, Got: {result}")
            
            if result == expected:
                print("✅ PASS")
            else:
                print("❌ FAIL")
                all_passed = False
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            all_passed = False
            
        print("-" * 40)
    
    if all_passed:
        print("\n🎉 All edge case tests passed!")
        return True
    else:
        print("\n❌ Some edge case tests failed!")
        return False


def main():
    """Run edge case tests."""
    print("Testing edge cases for mention detection fix...\n")
    
    # Set up logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    if test_edge_cases():
        print("✅ All edge cases handled correctly!")
        return 0
    else:
        print("❌ Some edge cases failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())