#!/usr/bin/env python3
"""
Integration test to validate that OpenRouter configuration works end-to-end.
This test focuses on the configuration loading and parameter generation.
"""
import os
import sys
import tempfile
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import Config

def test_openrouter_integration():
    """Test that OpenRouter configuration integrates properly."""
    print("=== Testing OpenRouter Integration ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up environment variables for OpenRouter with custom settings
        test_env_vars = {
            'MATRIX_HOMESERVER_URL': 'https://matrix.test.org',
            'MATRIX_USER_ID': '@testbot:matrix.test.org', 
            'MATRIX_PASSWORD': 'test_password_123',
            'MATRIX_STORE_PATH': os.path.join(temp_dir, 'matrix_store'),
            'DISCOURSE_BASE_URL': 'https://discourse.test.org',
            'LLM_PROVIDER': 'openrouter',
            'LLM_API_KEY': 'sk-or-test-key-123',
            'LLM_MODEL': 'anthropic/claude-3-haiku',
            'OPENROUTER_PROVIDER': 'anthropic',
            'OPENROUTER_ROUTE': 'fastest',
            'LOG_LEVEL': 'INFO'
        }
        
        # Set environment variables
        for key, value in test_env_vars.items():
            os.environ[key] = value
        
        try:
            # Initialize configuration
            config = Config()
            print("✓ Config initialized successfully")
            
            # Verify OpenRouter configuration
            assert config.llm_provider == 'openrouter'
            assert config.openrouter_provider == 'anthropic'
            assert config.openrouter_route == 'fastest'
            print("✓ OpenRouter configuration verified")
            
            # Test OpenAI client kwargs
            client_kwargs = config.get_openai_client_kwargs()
            expected_headers = {
                "HTTP-Referer": "https://github.com/aosus/askaosus",
                "X-Title": "Askaosus Matrix Bot",
            }
            assert client_kwargs["api_key"] == test_env_vars['LLM_API_KEY']
            assert client_kwargs["base_url"] == "https://openrouter.ai/api/v1"
            assert client_kwargs["default_headers"] == expected_headers
            print("✓ OpenAI client kwargs configured correctly")
            
            # Test OpenRouter parameters
            openrouter_params = config.get_openrouter_parameters()
            expected_params = {
                "provider": {"require": ["anthropic"]},
                "route": "fastest"
            }
            assert openrouter_params == expected_params
            print("✓ OpenRouter parameters generated correctly")
            
            return True
            
        except Exception as e:
            print(f"✗ OpenRouter integration test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Clean up environment variables
            for key in test_env_vars.keys():
                if key in os.environ:
                    del os.environ[key]

def test_parameter_combinations():
    """Test different combinations of OpenRouter parameters."""
    print("\n=== Testing Parameter Combinations ===")
    
    test_cases = [
        # Only provider
        {
            'OPENROUTER_PROVIDER': 'openai',
            'expected': {'provider': {'require': ['openai']}, 'route': 'best'}
        },
        # Only route  
        {
            'OPENROUTER_ROUTE': 'cheapest',
            'expected': {'route': 'cheapest'}
        },
        # Both provider and route
        {
            'OPENROUTER_PROVIDER': 'google',
            'OPENROUTER_ROUTE': 'fastest',
            'expected': {'provider': {'require': ['google']}, 'route': 'fastest'}
        },
        # Neither (defaults)
        {
            'expected': {'route': 'best'}
        }
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\nTest case {i + 1}:")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Base environment variables
            test_env_vars = {
                'MATRIX_HOMESERVER_URL': 'https://matrix.test.org',
                'MATRIX_USER_ID': '@testbot:matrix.test.org', 
                'MATRIX_PASSWORD': 'test_password_123',
                'MATRIX_STORE_PATH': os.path.join(temp_dir, 'matrix_store'),
                'LLM_PROVIDER': 'openrouter',
                'LLM_API_KEY': 'sk-or-test-key-123',
                'LLM_MODEL': 'anthropic/claude-3-haiku',
                'LOG_LEVEL': 'ERROR'  # Reduce logging for cleaner test output
            }
            
            # Add case-specific variables
            for key, value in case.items():
                if key != 'expected':
                    test_env_vars[key] = value
            
            # Set environment variables
            for key, value in test_env_vars.items():
                os.environ[key] = value
            
            try:
                config = Config()
                params = config.get_openrouter_parameters()
                expected = case['expected']
                
                assert params == expected, f"Expected {expected}, got {params}"
                print(f"✓ Parameters: {json.dumps(params, sort_keys=True)}")
                
            except Exception as e:
                print(f"✗ Test case {i + 1} failed: {e}")
                return False
            finally:
                # Clean up environment variables
                for key in test_env_vars.keys():
                    if key in os.environ:
                        del os.environ[key]
    
    print("✓ All parameter combination tests passed")
    return True

def main():
    """Run integration tests for OpenRouter configuration."""
    print("Running OpenRouter integration tests...")
    print(f"Python path: {sys.path[0]}")
    print(f"Current directory: {os.getcwd()}")
    
    success = True
    success &= test_openrouter_integration()
    success &= test_parameter_combinations()
    
    if success:
        print("\n🎉 All OpenRouter integration tests passed!")
        print("The OpenRouter provider and routing configuration is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some integration tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()