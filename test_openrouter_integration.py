#!/usr/bin/env python3
"""
Simple test to verify OpenRouter provider configuration integration.
Tests the logic without imports from other modules.
"""
import os
import sys
import json
import asyncio
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import Config

async def test_request_params_generation():
    """Test that request parameters are generated correctly with provider config."""
    print("=== Testing Request Parameters Generation ===")
    
    # Test 1: OpenRouter with sorting preference
    print("Testing OpenRouter with sorting preference...")
    os.environ["MATRIX_HOMESERVER_URL"] = "https://matrix.test.org"
    os.environ["MATRIX_USER_ID"] = "@testbot:matrix.test.org"
    os.environ["MATRIX_PASSWORD"] = "test_password"
    os.environ["LLM_API_KEY"] = "test_api_key"
    os.environ["LLM_PROVIDER"] = "openrouter"
    os.environ["LLM_OPENROUTER_SORTING"] = "throughput"
    
    # Clear provider setting if set
    if "LLM_OPENROUTER_PROVIDER" in os.environ:
        del os.environ["LLM_OPENROUTER_PROVIDER"]
    
    config = Config()
    provider_config = config.get_openrouter_provider_config()
    
    # Simulate how LLM client would build request
    request_params = {
        "model": config.llm_model,
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": config.llm_max_tokens,
        "temperature": config.llm_temperature,
    }
    
    if provider_config:
        request_params["provider"] = provider_config
    
    expected_provider = {"order": ["auto:throughput"]}
    if request_params.get("provider") == expected_provider:
        print("✓ Sorting preference correctly added to request parameters")
    else:
        print(f"✗ Wrong provider config: {request_params.get('provider')}, expected: {expected_provider}")
        return False
    
    # Test 2: OpenRouter with manual provider
    print("Testing OpenRouter with manual provider selection...")
    os.environ["LLM_OPENROUTER_PROVIDER"] = "anthropic"
    
    config2 = Config()
    provider_config2 = config2.get_openrouter_provider_config()
    
    request_params2 = {
        "model": config2.llm_model,
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": config2.llm_max_tokens,
        "temperature": config2.llm_temperature,
    }
    
    if provider_config2:
        request_params2["provider"] = provider_config2
    
    expected_provider2 = {"order": ["anthropic"]}
    if request_params2.get("provider") == expected_provider2:
        print("✓ Manual provider correctly added to request parameters (overriding sorting)")
    else:
        print(f"✗ Wrong provider config: {request_params2.get('provider')}, expected: {expected_provider2}")
        return False
    
    # Test 3: OpenAI provider (should not include provider config)
    print("Testing OpenAI provider (should exclude provider config)...")
    os.environ["LLM_PROVIDER"] = "openai"
    
    config3 = Config()
    provider_config3 = config3.get_openrouter_provider_config()
    
    request_params3 = {
        "model": config3.llm_model,
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": config3.llm_max_tokens,
        "temperature": config3.llm_temperature,
    }
    
    if provider_config3:
        request_params3["provider"] = provider_config3
    
    if "provider" not in request_params3:
        print("✓ Provider config correctly excluded for OpenAI")
    else:
        print(f"✗ Provider config found in OpenAI request: {request_params3.get('provider')}")
        return False
    
    print("\nExample request parameters for each case:")
    
    # Show example requests
    os.environ["LLM_PROVIDER"] = "openrouter"
    os.environ["LLM_OPENROUTER_SORTING"] = "price"
    del os.environ["LLM_OPENROUTER_PROVIDER"]
    config_sorting = Config()
    provider_sorting = config_sorting.get_openrouter_provider_config()
    print(f"  Sorting (price): provider = {provider_sorting}")
    
    os.environ["LLM_OPENROUTER_PROVIDER"] = "openai"
    config_manual = Config()
    provider_manual = config_manual.get_openrouter_provider_config()
    print(f"  Manual (openai): provider = {provider_manual}")
    
    os.environ["LLM_PROVIDER"] = "openai"
    config_openai = Config()
    provider_openai = config_openai.get_openrouter_provider_config()
    print(f"  OpenAI: provider = {provider_openai}")
    
    return True

def main():
    """Run the request parameter integration test."""
    print("Testing OpenRouter provider configuration request integration...")
    
    # Store original environment
    original_env = dict(os.environ)
    
    try:
        # Suppress logging during tests
        logging.getLogger().setLevel(logging.CRITICAL)
        
        success = asyncio.run(test_request_params_generation())
        
        print("\n=== Request Integration Test Results ===")
        if success:
            print("✅ OpenRouter provider configuration properly integrated into requests!")
        else:
            print("❌ OpenRouter provider configuration integration failed!")
        
        return success
        
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

def main():
    """Run the manual integration test."""
    import asyncio
    import logging
    
    # Suppress logging during tests
    logging.getLogger().setLevel(logging.CRITICAL)
    
    print("Testing OpenRouter provider configuration integration...")
    
    # Store original environment
    original_env = dict(os.environ)
    
    try:
        success = asyncio.run(test_openrouter_provider_in_request())
        
        print("\n=== Integration Test Results ===")
        if success:
            print("✅ OpenRouter provider configuration properly integrated!")
        else:
            print("❌ OpenRouter provider configuration integration failed!")
        
        return success
        
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)