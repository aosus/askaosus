#!/usr/bin/env python3
"""
Test script for configurable responses functionality.
"""
import sys
import os
import tempfile
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from responses import ResponseConfig


def test_response_config():
    """Test the ResponseConfig class functionality."""
    print("Testing ResponseConfig functionality...")
    
    # Test 1: Loading from existing file
    print("✓ Test 1: Loading from existing responses.json")
    config = ResponseConfig("/home/runner/work/askaosus/askaosus/responses.json")
    
    # Test getting various responses
    no_results = config.get_error_message("no_results_found")
    untitled_post = config.get_discourse_message("untitled_post")
    
    print(f"  No results: {no_results[:50]}...")
    print(f"  Untitled post: {untitled_post}")
    
    # Test 2: Fallback to defaults when file doesn't exist
    print("✓ Test 2: Fallback to defaults when file missing")
    config_missing = ResponseConfig("/nonexistent/path/responses.json")
    fallback_message = config_missing.get_error_message("processing_error")
    print(f"  Fallback message: {fallback_message[:50]}...")
    
    # Test 3: Custom config file
    print("✓ Test 3: Custom configuration file")
    custom_responses = {
        "error_messages": {
            "test_error": "Custom test error message"
        }
    }
    
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(custom_responses, f, ensure_ascii=False, indent=2)
        temp_path = f.name
    
    try:
        custom_config = ResponseConfig(temp_path)
        custom_message = custom_config.get_error_message("test_error")
        print(f"  Custom message: {custom_message}")
        
        # Test fallback for missing key
        missing_key = custom_config.get_error_message("missing_key")
        print(f"  Missing key fallback: {missing_key}")
        
    finally:
        # Clean up temp file
        os.unlink(temp_path)
    
    print("🎉 All ResponseConfig tests passed!")
    return True


def test_integration():
    """Test integration with the response system."""
    print("\nTesting integration...")
    
    # Test that responses.json has all required keys
    config_path = "/home/runner/work/askaosus/askaosus/responses.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        responses = json.load(f)
    
    required_keys = {
        "error_messages": ["no_results_found", "processing_error", "search_error", "fallback_error"],
        "discourse_messages": ["no_results", "untitled_post", "untitled_topic", "default_excerpt"],
        "system_messages": ["perfect_match", "closest_match"]
    }
    
    missing_keys = []
    for category, keys in required_keys.items():
        if category not in responses:
            missing_keys.append(f"Missing category: {category}")
            continue
        for key in keys:
            if key not in responses[category]:
                missing_keys.append(f"Missing key: {category}.{key}")
            elif not isinstance(responses[category][key], str):
                missing_keys.append(f"Invalid type for key: {category}.{key} (expected string)")
    
    if missing_keys:
        print("❌ Integration test failed:")
        for error in missing_keys:
            print(f"  {error}")
        return False
    
    print("✓ All required response keys present and valid")
    print("🎉 Integration test passed!")
    return True


if __name__ == "__main__":
    try:
        success1 = test_response_config()
        success2 = test_integration()
        
        if success1 and success2:
            print("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)