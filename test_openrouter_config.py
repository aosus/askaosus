#!/usr/bin/env python3
"""
Test script to validate OpenRouter provider configuration functionality.
"""
import os
import sys
import tempfile
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import Config

def test_openrouter_sorting_config():
    """Test OpenRouter sorting configuration."""
    print("=== Testing OpenRouter Sorting Configuration ===")
    
    # Test valid sorting options
    valid_options = ["throughput", "latency", "price"]
    
    for option in valid_options:
        print(f"Testing sorting option: {option}")
        
        # Set environment variables
        os.environ["MATRIX_HOMESERVER_URL"] = "https://matrix.test.org"
        os.environ["MATRIX_USER_ID"] = "@testbot:matrix.test.org"
        os.environ["MATRIX_PASSWORD"] = "test_password"
        os.environ["LLM_API_KEY"] = "test_api_key"
        os.environ["LLM_PROVIDER"] = "openrouter"
        os.environ["LLM_OPENROUTER_SORTING"] = option
        
        # Remove provider setting if set
        if "LLM_OPENROUTER_PROVIDER" in os.environ:
            del os.environ["LLM_OPENROUTER_PROVIDER"]
        
        try:
            config = Config()
            provider_config = config.get_openrouter_provider_config()
            
            # Verify configuration
            assert config.llm_openrouter_sorting == option
            assert provider_config is not None
            assert "order" in provider_config
            assert provider_config["order"] == [f"auto:{option}"]
            
            print(f"✓ {option} sorting configured correctly")
        except Exception as e:
            print(f"✗ {option} sorting failed: {e}")
            return False
    
    return True

def test_openrouter_manual_provider():
    """Test OpenRouter manual provider selection."""
    print("=== Testing OpenRouter Manual Provider Selection ===")
    
    # Test manual provider override
    test_provider = "anthropic"
    
    # Set environment variables
    os.environ["MATRIX_HOMESERVER_URL"] = "https://matrix.test.org"
    os.environ["MATRIX_USER_ID"] = "@testbot:matrix.test.org"
    os.environ["MATRIX_PASSWORD"] = "test_password"
    os.environ["LLM_API_KEY"] = "test_api_key"
    os.environ["LLM_PROVIDER"] = "openrouter"
    os.environ["LLM_OPENROUTER_SORTING"] = "throughput"  # Should be overridden
    os.environ["LLM_OPENROUTER_PROVIDER"] = test_provider
    
    try:
        config = Config()
        provider_config = config.get_openrouter_provider_config()
        
        # Verify that manual provider overrides sorting
        assert config.llm_openrouter_provider == test_provider
        assert provider_config is not None
        assert "order" in provider_config
        assert provider_config["order"] == [test_provider]
        
        print(f"✓ Manual provider '{test_provider}' configured correctly (overriding sorting)")
        return True
    except Exception as e:
        print(f"✗ Manual provider configuration failed: {e}")
        return False

def test_openrouter_disabled_for_other_providers():
    """Test that OpenRouter config is ignored for other providers."""
    print("=== Testing OpenRouter Config Disabled for Other Providers ===")
    
    # Set environment variables for OpenAI provider
    os.environ["MATRIX_HOMESERVER_URL"] = "https://matrix.test.org"
    os.environ["MATRIX_USER_ID"] = "@testbot:matrix.test.org"
    os.environ["MATRIX_PASSWORD"] = "test_password"
    os.environ["LLM_API_KEY"] = "test_api_key"
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_OPENROUTER_SORTING"] = "throughput"
    os.environ["LLM_OPENROUTER_PROVIDER"] = "anthropic"
    
    try:
        config = Config()
        provider_config = config.get_openrouter_provider_config()
        
        # Should return None for non-OpenRouter providers
        assert provider_config is None
        
        print("✓ OpenRouter config properly ignored for OpenAI provider")
        return True
    except Exception as e:
        print(f"✗ Provider config test failed: {e}")
        return False

def test_invalid_sorting_option():
    """Test validation of invalid sorting options."""
    print("=== Testing Invalid Sorting Option Validation ===")
    
    # Set environment variables with invalid sorting
    os.environ["MATRIX_HOMESERVER_URL"] = "https://matrix.test.org"
    os.environ["MATRIX_USER_ID"] = "@testbot:matrix.test.org"
    os.environ["MATRIX_PASSWORD"] = "test_password"
    os.environ["LLM_API_KEY"] = "test_api_key"
    os.environ["LLM_PROVIDER"] = "openrouter"
    os.environ["LLM_OPENROUTER_SORTING"] = "invalid_option"
    
    try:
        config = Config()
        print("✗ Invalid sorting option should have raised ValueError")
        return False
    except ValueError as e:
        if "Invalid LLM_OPENROUTER_SORTING" in str(e):
            print("✓ Invalid sorting option properly rejected")
            return True
        else:
            print(f"✗ Wrong error message: {e}")
            return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def main():
    """Run all OpenRouter configuration tests."""
    print("Testing OpenRouter provider configuration...")
    
    # Store original environment to restore later
    original_env = dict(os.environ)
    
    try:
        # Suppress logging during tests
        logging.getLogger().setLevel(logging.CRITICAL)
        
        # Run tests
        tests = [
            test_openrouter_sorting_config,
            test_openrouter_manual_provider,
            test_openrouter_disabled_for_other_providers,
            test_invalid_sorting_option,
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
            print()  # Add spacing between tests
        
        # Results
        print("=== OpenRouter Configuration Test Results ===")
        print(f"Passed: {passed}/{total}")
        
        if passed == total:
            print("✅ All OpenRouter configuration tests passed!")
            return True
        else:
            print("❌ Some OpenRouter configuration tests failed!")
            return False
            
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)