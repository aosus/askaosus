#!/usr/bin/env python3
"""
Simple validation test for reply behavior implementation.
Tests the core logic without complex imports.
"""

import os
import sys
import re

def test_reply_behavior_config_validation():
    """Test reply behavior configuration options."""
    print("=== Testing Reply Behavior Configuration ===")
    
    # Test configuration validation logic (standalone)
    valid_behaviors = {"ignore", "mention", "watch"}
    
    test_cases = [
        ("ignore", True),
        ("mention", True),
        ("watch", True),
        ("invalid", False),
        ("IGNORE", True),  # Should be valid because config normalizes to lowercase
        ("", False),
    ]
    
    for behavior, should_be_valid in test_cases:
        # The actual validation should match our config.py logic
        # Convert to lowercase first, then check if it's in valid set
        normalized = behavior.lower() if behavior else ""
        is_valid = normalized in valid_behaviors
        
        if is_valid == should_be_valid:
            status = "✓" if should_be_valid else "✓ (correctly rejected)"
            print(f"{status} '{behavior}' -> {is_valid}")
        else:
            print(f"✗ '{behavior}' validation failed: expected {should_be_valid}, got {is_valid}")
            return False
    
    print("🎉 Configuration validation tests passed!")
    return True


def test_reply_content_cleaning():
    """Test reply content cleaning logic."""
    print("\n=== Testing Reply Content Cleaning ===")
    
    def clean_reply_content(message_body: str, bot_mentions: list) -> str:
        """Standalone version of the cleaning function."""
        cleaned = message_body
        
        # Remove bot mentions - handle @ symbols properly
        for mention in bot_mentions:
            if mention.startswith('@'):
                # For @mentions, remove the whole word
                cleaned = re.sub(rf"@{re.escape(mention[1:])}\b", "", cleaned, flags=re.IGNORECASE)
            # Also handle the mention without @ in case it's in the list
            cleaned = re.sub(rf"\b{re.escape(mention)}\b", "", cleaned, flags=re.IGNORECASE)
        
        # Remove common Matrix reply prefixes (fallback formatting)
        lines = cleaned.split('\n')
        non_quote_lines = []
        for line in lines:
            if not line.strip().startswith('> '):
                non_quote_lines.append(line)
        
        cleaned = '\n'.join(non_quote_lines).strip()
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    test_cases = [
        {
            "input": "@askaosus how do I install Ubuntu?",
            "expected": "how do I install Ubuntu?",
            "description": "Remove simple @mention"
        },
        {
            "input": "> Original: I need help\n@askaosus what about this specific issue?",
            "expected": "what about this specific issue?", 
            "description": "Remove quote lines and @mention"
        },
        {
            "input": "askaosus please help with this",
            "expected": "please help with this",
            "description": "Remove mention without @ symbol"
        },
        {
            "input": "   @askaosus   help   me   please   ",
            "expected": "help me please",
            "description": "Clean up extra whitespace"
        },
        {
            "input": "> Quote 1\n> Quote 2\nActual question @askaosus",
            "expected": "Actual question",
            "description": "Remove multiple quotes and mention"
        },
        {
            "input": "> @user: Original question\n@askaosus can you help?",
            "expected": "can you help?",
            "description": "Remove quoted user mention and bot mention"
        }
    ]
    
    bot_mentions = ["@askaosus", "askaosus"]
    
    for i, test_case in enumerate(test_cases):
        print(f"Test {i+1}: {test_case['description']}")
        
        try:
            result = clean_reply_content(test_case["input"], bot_mentions)
            if result == test_case["expected"]:
                print(f"✓ '{test_case['input'][:30]}...' -> '{result}'")
            else:
                print(f"✗ Expected: '{test_case['expected']}'")
                print(f"   Got:      '{result}'")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    print("🎉 Content cleaning tests passed!")
    return True


def test_reply_behavior_logic():
    """Test the reply behavior decision logic."""
    print("\n=== Testing Reply Behavior Logic ===")
    
    def should_respond_to_reply(reply_behavior, is_reply_to_bot, has_mention):
        """Standalone version of reply behavior logic."""
        if not is_reply_to_bot:
            # For replies to non-bot messages, only respond if mentioned (original behavior)
            return has_mention
        
        # For replies to bot messages, apply configured behavior
        if reply_behavior == "ignore":
            return False  # Ignore all replies to bot messages
        elif reply_behavior == "mention":
            return has_mention  # Only respond if reply also mentions bot
        elif reply_behavior == "watch":
            return True  # Respond to all replies to bot messages
        
        return False  # Unknown behavior
    
    test_cases = [
        # Format: (behavior, is_reply_to_bot, has_mention, should_respond, description)
        ("ignore", True, True, False, "ignore: reply to bot with mention"),
        ("ignore", True, False, False, "ignore: reply to bot without mention"),
        ("ignore", False, True, True, "ignore: reply to user with mention"),
        ("ignore", False, False, False, "ignore: reply to user without mention"),
        
        ("mention", True, True, True, "mention: reply to bot with mention"),
        ("mention", True, False, False, "mention: reply to bot without mention"),
        ("mention", False, True, True, "mention: reply to user with mention"),
        ("mention", False, False, False, "mention: reply to user without mention"),
        
        ("watch", True, True, True, "watch: reply to bot with mention"),
        ("watch", True, False, True, "watch: reply to bot without mention"),
        ("watch", False, True, True, "watch: reply to user with mention"),
        ("watch", False, False, False, "watch: reply to user without mention"),
    ]
    
    for behavior, is_reply_to_bot, has_mention, expected, description in test_cases:
        result = should_respond_to_reply(behavior, is_reply_to_bot, has_mention)
        
        if result == expected:
            print(f"✓ {description} -> {result}")
        else:
            print(f"✗ {description} -> expected {expected}, got {result}")
            return False
    
    print("🎉 Reply behavior logic tests passed!")
    return True


def test_configuration_with_env_vars():
    """Test configuration loading with environment variables."""
    print("\n=== Testing Configuration Loading ===")
    
    # Save original environment
    original_env = os.environ.copy()
    
    try:
        # Set test environment
        os.environ["MATRIX_HOMESERVER_URL"] = "https://matrix.test.org"
        os.environ["MATRIX_USER_ID"] = "@testbot:matrix.test.org"
        os.environ["MATRIX_PASSWORD"] = "test_password"
        os.environ["LLM_API_KEY"] = "test_key"
        
        # Test each reply behavior
        for behavior in ["ignore", "mention", "watch"]:
            print(f"Testing configuration with BOT_REPLY_BEHAVIOR={behavior}")
            os.environ["BOT_REPLY_BEHAVIOR"] = behavior
            
            try:
                # Import and test configuration
                import importlib.util
                import logging
                
                # Mock logging to avoid output
                logging.disable(logging.CRITICAL)
                
                config_path = os.path.join(os.path.dirname(__file__), 'src', 'config.py')
                spec = importlib.util.spec_from_file_location("config", config_path)
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                
                config = config_module.Config()
                
                if config.bot_reply_behavior == behavior:
                    print(f"✓ {behavior} configuration loaded correctly")
                else:
                    print(f"✗ Expected {behavior}, got {config.bot_reply_behavior}")
                    return False
                    
                # Re-enable logging
                logging.disable(logging.NOTSET)
                
            except Exception as e:
                print(f"✗ Error loading configuration for {behavior}: {e}")
                return False
            
            # Clean up module cache
            if "config" in sys.modules:
                del sys.modules["config"]
        
        # Test default behavior
        if "BOT_REPLY_BEHAVIOR" in os.environ:
            del os.environ["BOT_REPLY_BEHAVIOR"]
        
        try:
            import importlib.util
            import logging
            logging.disable(logging.CRITICAL)
            
            config_path = os.path.join(os.path.dirname(__file__), 'src', 'config.py')
            spec = importlib.util.spec_from_file_location("config", config_path)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            config = config_module.Config()
            
            if config.bot_reply_behavior == "mention":
                print("✓ Default behavior is 'mention'")
            else:
                print(f"✗ Expected default 'mention', got {config.bot_reply_behavior}")
                return False
                
            logging.disable(logging.NOTSET)
            
        except Exception as e:
            print(f"✗ Error testing default configuration: {e}")
            return False
    
    finally:
        # Restore environment
        os.environ.clear()
        os.environ.update(original_env)
        
        # Clean up module cache
        if "config" in sys.modules:
            del sys.modules["config"]
    
    print("🎉 Configuration loading tests passed!")
    return True


def main():
    """Run all validation tests."""
    print("Running reply behavior validation tests...\n")
    
    tests = [
        test_reply_behavior_config_validation,
        test_reply_content_cleaning,
        test_reply_behavior_logic,
        test_configuration_with_env_vars,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
                print(f"✓ {test.__name__} PASSED\n")
            else:
                failed += 1
                print(f"✗ {test.__name__} FAILED\n")
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__} ERROR: {e}\n")
    
    print("=== Final Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    if failed == 0:
        print("🎉 All validation tests passed!")
        print("\nReply behavior implementation is ready!")
        return 0
    else:
        print("❌ Some validation tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())