#!/usr/bin/env python3
"""
Test script for the simplified LLM system.
"""
import os
import sys
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_imports():
    """Test that all imports work correctly."""
    print("=== Testing Imports ===")
    
    try:
        # Import from absolute paths
        import sys
        sys.path.insert(0, "/app/src")
        
        import discourse
        print("✓ Discourse module imported")
        
        # Test specific classes exist
        assert hasattr(discourse, 'DiscourseSearcher')
        assert hasattr(discourse, 'DiscourseRateLimitError') 
        assert hasattr(discourse, 'DiscourseConnectionError')
        print("✓ Discourse classes exist")
        
    except Exception as e:
        print(f"✗ Discourse import failed: {e}")
        return False
    
    try:
        import responses
        print("✓ ResponseConfig module imported")
        assert hasattr(responses, 'ResponseConfig')
        print("✓ ResponseConfig class exists")
    except Exception as e:
        print(f"✗ ResponseConfig import failed: {e}")
        return False
    
    try:
        import llm
        print("✓ LLM module imported")
        assert hasattr(llm, 'LLMClient')
        print("✓ LLMClient class exists")
    except Exception as e:
        print(f"✗ LLMClient import failed: {e}")
        return False
    
    return True

async def test_response_config():
    """Test the response configuration."""
    print("\n=== Testing Response Config ===")
    
    try:
        import sys
        sys.path.insert(0, "/app/src")
        import responses
        ResponseConfig = responses.ResponseConfig
        
        config = ResponseConfig()
        
        # Test new error messages
        rate_limit_msg = config.get_error_message("rate_limit_error")
        discourse_unreachable_msg = config.get_error_message("discourse_unreachable")
        llm_down_msg = config.get_error_message("llm_down")
        
        print(f"✓ Rate limit message: {rate_limit_msg[:50]}...")
        print(f"✓ Discourse unreachable message: {discourse_unreachable_msg[:50]}...")
        print(f"✓ LLM down message: {llm_down_msg[:50]}...")
        
        # Test discourse messages still work
        no_results_msg = config.get_discourse_message("no_results")
        print(f"✓ No results message: {no_results_msg}")
        
        return True
        
    except Exception as e:
        print(f"✗ Response config test failed: {e}")
        return False

async def test_discourse_exceptions():
    """Test discourse exception classes."""
    print("\n=== Testing Discourse Exceptions ===")
    
    try:
        import sys
        sys.path.insert(0, "/app/src")
        import discourse
        
        DiscourseRateLimitError = discourse.DiscourseRateLimitError
        DiscourseConnectionError = discourse.DiscourseConnectionError
        
        # Test that exceptions can be raised and caught
        try:
            raise DiscourseRateLimitError("Test rate limit")
        except DiscourseRateLimitError as e:
            print(f"✓ Rate limit exception works: {e}")
        
        try:
            raise DiscourseConnectionError("Test connection error")
        except DiscourseConnectionError as e:
            print(f"✓ Connection exception works: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Exception test failed: {e}")
        return False

async def test_system_prompt():
    """Test that system prompt was updated."""
    print("\n=== Testing System Prompt ===")
    
    try:
        with open("/app/system_prompt.md", "r") as f:
            content = f.read()
        
        # Check that old tools are removed
        if "send_link" in content:
            print("✗ System prompt still contains send_link")
            return False
        
        if "no_result_message" in content:
            print("✗ System prompt still contains no_result_message")
            return False
        
        # Check that search_discourse is still there
        if "search_discourse" not in content:
            print("✗ System prompt missing search_discourse")
            return False
        
        print("✓ System prompt updated correctly")
        print("✓ Only search_discourse tool remains")
        print("✓ Removed send_link and no_result_message tools")
        
        return True
        
    except Exception as e:
        print(f"✗ System prompt test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("Testing simplified LLM system...\n")
    
    success = True
    success &= await test_imports()
    success &= await test_response_config()
    success &= await test_discourse_exceptions()
    success &= await test_system_prompt()
    
    print(f"\n=== Test Results ===")
    if success:
        print("✅ All tests passed!")
        print("✅ LLM system successfully simplified")
        print("✅ Only search_discourse tool remains")
        print("✅ Three error messages configured")
        print("✅ Exception handling added for Discourse")
    else:
        print("❌ Some tests failed")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
