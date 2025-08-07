#!/usr/bin/env python3
"""
Final smoke test to verify the complete OpenRouter configuration works
in a realistic scenario.
"""
import os
import sys
import tempfile
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_complete_configuration():
    """Test complete configuration including OpenRouter features."""
    print("=== Final Smoke Test: Complete OpenRouter Configuration ===")
    
    # Store original environment
    original_env = dict(os.environ)
    
    try:
        # Set up realistic configuration
        test_env = {
            "MATRIX_HOMESERVER_URL": "https://matrix.aosus.org",
            "MATRIX_USER_ID": "@askaosus:matrix.aosus.org", 
            "MATRIX_PASSWORD": "secure_password_123",
            "LLM_API_KEY": "sk-or-v1-test_api_key",
            "LLM_PROVIDER": "openrouter",
            "LLM_MODEL": "anthropic/claude-3.5-sonnet",
            "LLM_OPENROUTER_SORTING": "latency",
            "BOT_UTM_TAGS": "utm_source=bot&utm_medium=matrix&utm_campaign=help"
        }
        
        # Apply test environment
        for key, value in test_env.items():
            os.environ[key] = value
        
        # Test 1: Configuration loads correctly
        print("1. Loading configuration...")
        from config import Config
        config = Config()
        
        assert config.llm_provider == "openrouter"
        assert config.llm_openrouter_sorting == "latency"
        assert config.llm_openrouter_provider == ""
        print("   ✓ Configuration loaded successfully")
        
        # Test 2: OpenRouter provider config generation
        print("2. Testing OpenRouter provider configuration...")
        provider_config = config.get_openrouter_provider_config()
        expected = {"order": ["auto:latency"]}
        assert provider_config == expected, f"Expected {expected}, got {provider_config}"
        print("   ✓ Provider configuration generated correctly")
        
        # Test 3: OpenAI client kwargs generation
        print("3. Testing OpenAI client configuration...")
        client_kwargs = config.get_openai_client_kwargs()
        expected_headers = {
            "HTTP-Referer": "https://github.com/aosus/askaosus",
            "X-Title": "Askaosus Matrix Bot",
        }
        
        assert client_kwargs["api_key"] == "sk-or-v1-test_api_key"
        assert client_kwargs["base_url"] == "https://openrouter.ai/api/v1"
        assert client_kwargs["default_headers"] == expected_headers
        print("   ✓ Client configuration includes OpenRouter headers")
        
        # Test 4: UTM tag functionality
        print("4. Testing UTM tag functionality...")
        test_url = "https://discourse.aosus.org/t/test-topic/123"
        tagged_url = config.add_utm_tags_to_url(test_url)
        
        assert "utm_source=bot" in tagged_url
        assert "utm_medium=matrix" in tagged_url
        assert "utm_campaign=help" in tagged_url
        print("   ✓ UTM tags added to URLs correctly")
        
        # Test 5: Manual provider override
        print("5. Testing manual provider override...")
        os.environ["LLM_OPENROUTER_PROVIDER"] = "openai"
        
        config_override = Config()
        provider_override = config_override.get_openrouter_provider_config()
        expected_override = {"order": ["openai"]}
        
        assert provider_override == expected_override
        print("   ✓ Manual provider correctly overrides sorting")
        
        # Test 6: Simulate request parameters (like LLM client would use)
        print("6. Testing LLM request parameter integration...")
        
        # Typical request parameters
        request_params = {
            "model": config_override.llm_model,
            "messages": [{"role": "user", "content": "How do I install Ubuntu?"}],
            "max_tokens": config_override.llm_max_tokens,
            "temperature": config_override.llm_temperature,
        }
        
        # Add provider config (like llm.py does)
        openrouter_provider = config_override.get_openrouter_provider_config()
        if openrouter_provider:
            request_params["provider"] = openrouter_provider
        
        assert "provider" in request_params
        assert request_params["provider"] == {"order": ["openai"]}
        print("   ✓ Request parameters include provider configuration")
        
        print("\n🎉 ALL TESTS PASSED!")
        print("\n=== Configuration Summary ===")
        print(f"   LLM Provider: {config.llm_provider}")
        print(f"   OpenRouter Sorting: {config.llm_openrouter_sorting}")
        print(f"   OpenRouter Provider: {config_override.llm_openrouter_provider}")
        print(f"   UTM Tags: {config.utm_tags}")
        print(f"   Provider Config: {openrouter_provider}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

def main():
    """Run the final smoke test."""
    print("Running comprehensive OpenRouter configuration test...")
    
    # Suppress logging during test
    import logging
    logging.getLogger().setLevel(logging.CRITICAL)
    
    success = test_complete_configuration()
    
    print("\n=== Final Test Results ===")
    if success:
        print("✅ OpenRouter configuration implementation is working correctly!")
        print("   Ready for production use with both sorting and manual provider selection.")
    else:
        print("❌ OpenRouter configuration implementation has issues!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)