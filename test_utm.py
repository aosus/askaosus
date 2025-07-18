#!/usr/bin/env python3
"""
Simple test script to verify UTM tag functionality.
Run this script to test the UTM tag feature without running the full bot.
"""

import os
import sys
sys.path.insert(0, '/app/src')

from config import Config

def test_utm_tags():
    """Test UTM tag functionality."""
    print("Testing UTM tag functionality...")
    
    # Test 1: No UTM tags configured
    os.environ.pop('BOT_UTM_TAGS', None)
    config = Config()
    original_url = "https://discourse.aosus.org/t/test-topic/123"
    result = config.add_utm_tags_to_url(original_url)
    assert result == original_url, f"Expected {original_url}, got {result}"
    print("✓ Test 1 passed: No UTM tags - URL unchanged")
    
    # Test 2: Simple UTM tags
    os.environ['BOT_UTM_TAGS'] = "utm_source=bot&utm_medium=matrix"
    config = Config()
    result = config.add_utm_tags_to_url(original_url)
    expected = "https://discourse.aosus.org/t/test-topic/123?utm_source=bot&utm_medium=matrix"
    assert "utm_source=bot" in result and "utm_medium=matrix" in result, f"UTM tags not found in {result}"
    print("✓ Test 2 passed: Simple UTM tags added")
    
    # Test 3: URL with existing parameters
    url_with_params = "https://discourse.aosus.org/search?q=test"
    os.environ['BOT_UTM_TAGS'] = "utm_source=bot&utm_campaign=test"
    config = Config()
    result = config.add_utm_tags_to_url(url_with_params)
    assert "q=test" in result and "utm_source=bot" in result and "utm_campaign=test" in result, f"Parameters not preserved in {result}"
    print("✓ Test 3 passed: Existing parameters preserved")
    
    # Test 4: Complex UTM tags
    os.environ['BOT_UTM_TAGS'] = "utm_source=matrix_bot&utm_medium=matrix&utm_campaign=user_support&utm_content=auto_response"
    config = Config()
    result = config.add_utm_tags_to_url(original_url)
    expected_params = ["utm_source=matrix_bot", "utm_medium=matrix", "utm_campaign=user_support", "utm_content=auto_response"]
    for param in expected_params:
        assert param in result, f"Expected parameter {param} not found in {result}"
    print("✓ Test 4 passed: Complex UTM tags added")
    
    # Test 5: Invalid format handling
    os.environ['BOT_UTM_TAGS'] = "invalid_format_no_equals"
    config = Config()
    result = config.add_utm_tags_to_url(original_url)
    # Should return original URL on error
    assert result == original_url, f"Expected fallback to original URL, got {result}"
    print("✓ Test 5 passed: Invalid format handled gracefully")
    
    print("\n🎉 All UTM tag tests passed!")

if __name__ == "__main__":
    # Set minimal required environment variables for Config
    os.environ.setdefault('MATRIX_HOMESERVER_URL', 'https://matrix.org')
    os.environ.setdefault('MATRIX_USER_ID', '@test:matrix.org')
    os.environ.setdefault('MATRIX_PASSWORD', 'test')
    os.environ.setdefault('LLM_API_KEY', 'test')
    
    try:
        test_utm_tags()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
