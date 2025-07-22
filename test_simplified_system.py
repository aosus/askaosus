#!/usr/bin/env python3
"""
Simple test to verify the key changes are working.
"""

def test_responses_file():
    """Test that responses.json has the new error messages."""
    import json
    
    with open("/app/responses.json", "r") as f:
        data = json.load(f)
    
    # Check new error messages exist
    error_messages = data.get("error_messages", {})
    
    required_errors = ["rate_limit_error", "discourse_unreachable", "llm_down"]
    for error_key in required_errors:
        if error_key not in error_messages:
            print(f"✗ Missing error message: {error_key}")
            return False
        print(f"✓ Found error message: {error_key}")
    
    # Check old error messages are removed
    old_errors = ["no_results_found", "processing_error", "search_error", "fallback_error"]
    for error_key in old_errors:
        if error_key in error_messages:
            print(f"✗ Old error message still present: {error_key}")
            return False
    
    print("✓ Old error messages properly removed")
    
    # Check system_messages section is removed
    if "system_messages" in data:
        print("✗ system_messages section still present")
        return False
    
    print("✓ system_messages section removed")
    
    return True

def test_system_prompt():
    """Test that system_prompt.md is updated."""
    with open("/app/system_prompt.md", "r") as f:
        content = f.read()
    
    # Check deprecated tools are removed
    if "send_link" in content or "no_result_message" in content:
        print("✗ Deprecated tools still in system prompt")
        return False
    
    print("✓ Deprecated tools removed from system prompt")
    
    # Check search_discourse is still there
    if "search_discourse" not in content:
        print("✗ search_discourse missing from system prompt")
        return False
    
    print("✓ search_discourse tool still present")
    
    return True

def test_discourse_exceptions():
    """Test that new exception classes are in discourse.py."""
    with open("/app/src/discourse.py", "r") as f:
        content = f.read()
    
    if "class DiscourseRateLimitError(Exception):" not in content:
        print("✗ DiscourseRateLimitError class missing")
        return False
    
    if "class DiscourseConnectionError(Exception):" not in content:
        print("✗ DiscourseConnectionError class missing")
        return False
    
    if "response.status == 429:" not in content:
        print("✗ Rate limit detection (429) missing")
        return False
    
    print("✓ New exception classes and rate limit detection added")
    
    return True

def test_llm_simplified():
    """Test that LLM client is simplified."""
    with open("/app/src/llm.py", "r") as f:
        content = f.read()
    
    # Check tools definition only has search_discourse
    tools_section = content[content.find("# Define tools for the LLM"):content.find("# Prepare messages")]
    
    if "send_link" in tools_section or "no_result_message" in tools_section:
        print("✗ Deprecated tools still in LLM tools definition")
        return False
    
    if tools_section.count('"name": "search_discourse"') != 1:
        print("✗ search_discourse tool not properly configured")
        return False
    
    print("✓ LLM tools simplified to only search_discourse")
    
    # Check error handling uses new error messages
    if "rate_limit_error" not in content:
        print("✗ rate_limit_error not used in LLM")
        return False
    
    if "discourse_unreachable" not in content:
        print("✗ discourse_unreachable not used in LLM")
        return False
    
    if "llm_down" not in content:
        print("✗ llm_down not used in LLM")
        return False
    
    print("✓ New error messages used in LLM")
    
    # Check UTM functionality is preserved
    if "_add_utm_tags_to_response" not in content:
        print("✗ UTM tag functionality missing")
        return False
    
    print("✓ UTM tag functionality preserved")
    
    return True

def main():
    """Run all tests."""
    print("=== Testing Simplified LLM System ===\n")
    
    tests = [
        ("Responses File", test_responses_file),
        ("System Prompt", test_system_prompt),
        ("Discourse Exceptions", test_discourse_exceptions),
        ("LLM Simplified", test_llm_simplified),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        try:
            if test_func():
                print(f"✅ {test_name} - PASSED\n")
            else:
                print(f"❌ {test_name} - FAILED\n")
                all_passed = False
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {e}\n")
            all_passed = False
    
    print("=== Summary ===")
    if all_passed:
        print("🎉 All tests passed!")
        print("✅ LLM system successfully simplified")
        print("✅ Only search_discourse tool remains")
        print("✅ Three new error messages configured")
        print("✅ Discourse error handling added")
        print("✅ UTM tracking preserved")
        print("✅ System prompt updated")
        print("✅ Response templates cleaned up")
    else:
        print("❌ Some tests failed - check output above")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
