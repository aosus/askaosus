#!/usr/bin/env python3
"""
Test script to validate OpenRouter-specific configuration parameters.
"""
import os
import sys
import tempfile
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import Config

def test_openrouter_defaults():
    """Test that OpenRouter defaults are set correctly."""
    print("=== Testing OpenRouter Default Configuration ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up minimal required environment variables for testing
        test_env_vars = {
            'MATRIX_HOMESERVER_URL': 'https://matrix.test.org',
            'MATRIX_USER_ID': '@testbot:matrix.test.org', 
            'MATRIX_PASSWORD': 'test_password_123',
            'MATRIX_STORE_PATH': os.path.join(temp_dir, 'matrix_store'),
            'LLM_PROVIDER': 'openrouter',
            'LLM_API_KEY': 'test_openrouter_key_123',
            'LLM_MODEL': 'anthropic/claude-3-haiku',
            'LOG_LEVEL': 'INFO'
        }
        
        # Set environment variables
        for key, value in test_env_vars.items():
            os.environ[key] = value
        
        try:
            config = Config()
            print("✓ OpenRouter configuration loaded successfully")
            
            # Test default values
            assert config.llm_provider == 'openrouter'
            assert config.openrouter_provider == ""  # Empty by default
            assert config.openrouter_route == "best"  # Default route
            
            print("✓ OpenRouter defaults are correct")
            
            # Test OpenRouter parameters method
            params = config.get_openrouter_parameters()
            expected_params = {"route": "best"}  # Only route should be set with default
            assert params == expected_params, f"Expected {expected_params}, got {params}"
            
            print("✓ Default OpenRouter parameters generated correctly")
            
            # Test that base URL is set correctly for OpenRouter
            assert config.llm_base_url == "https://openrouter.ai/api/v1"
            print("✓ OpenRouter base URL set correctly")
            
            return True
            
        except Exception as e:
            print(f"✗ OpenRouter default configuration failed: {e}")
            return False
        finally:
            # Clean up environment variables
            for key in test_env_vars.keys():
                if key in os.environ:
                    del os.environ[key]

def test_openrouter_custom_config():
    """Test OpenRouter with custom provider and route configuration."""
    print("\n=== Testing OpenRouter Custom Configuration ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up environment variables with custom OpenRouter config
        test_env_vars = {
            'MATRIX_HOMESERVER_URL': 'https://matrix.test.org',
            'MATRIX_USER_ID': '@testbot:matrix.test.org', 
            'MATRIX_PASSWORD': 'test_password_123',
            'MATRIX_STORE_PATH': os.path.join(temp_dir, 'matrix_store'),
            'LLM_PROVIDER': 'openrouter',
            'LLM_API_KEY': 'test_openrouter_key_123',
            'LLM_MODEL': 'anthropic/claude-3-haiku',
            'OPENROUTER_PROVIDER': 'anthropic',
            'OPENROUTER_ROUTE': 'cheapest',
            'LOG_LEVEL': 'INFO'
        }
        
        # Set environment variables
        for key, value in test_env_vars.items():
            os.environ[key] = value
        
        try:
            config = Config()
            print("✓ Custom OpenRouter configuration loaded successfully")
            
            # Test custom values
            assert config.llm_provider == 'openrouter'
            assert config.openrouter_provider == 'anthropic'
            assert config.openrouter_route == 'cheapest'
            
            print("✓ Custom OpenRouter values are correct")
            
            # Test OpenRouter parameters method with custom values
            params = config.get_openrouter_parameters()
            expected_params = {
                "provider": {"require": ["anthropic"]},
                "route": "cheapest"
            }
            assert params == expected_params, f"Expected {expected_params}, got {params}"
            
            print("✓ Custom OpenRouter parameters generated correctly")
            
            return True
            
        except Exception as e:
            print(f"✗ Custom OpenRouter configuration failed: {e}")
            return False
        finally:
            # Clean up environment variables
            for key in test_env_vars.keys():
                if key in os.environ:
                    del os.environ[key]

def test_openrouter_invalid_route():
    """Test that invalid OpenRouter routes are rejected."""
    print("\n=== Testing OpenRouter Invalid Route Validation ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up environment variables with invalid route
        test_env_vars = {
            'MATRIX_HOMESERVER_URL': 'https://matrix.test.org',
            'MATRIX_USER_ID': '@testbot:matrix.test.org', 
            'MATRIX_PASSWORD': 'test_password_123',
            'MATRIX_STORE_PATH': os.path.join(temp_dir, 'matrix_store'),
            'LLM_PROVIDER': 'openrouter',
            'LLM_API_KEY': 'test_openrouter_key_123',
            'LLM_MODEL': 'anthropic/claude-3-haiku',
            'OPENROUTER_ROUTE': 'invalid_route',
            'LOG_LEVEL': 'INFO'
        }
        
        # Set environment variables
        for key, value in test_env_vars.items():
            os.environ[key] = value
        
        try:
            config = Config()
            print("✗ Expected validation error for invalid route")
            return False
            
        except ValueError as e:
            if "Invalid OPENROUTER_ROUTE" in str(e):
                print("✓ Invalid route correctly rejected")
                return True
            else:
                print(f"✗ Wrong error for invalid route: {e}")
                return False
        except Exception as e:
            print(f"✗ Unexpected error for invalid route: {e}")
            return False
        finally:
            # Clean up environment variables
            for key in test_env_vars.keys():
                if key in os.environ:
                    del os.environ[key]

def test_non_openrouter_provider():
    """Test that OpenRouter parameters are not used for non-OpenRouter providers."""
    print("\n=== Testing Non-OpenRouter Provider ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up environment variables with OpenRouter vars but different provider
        test_env_vars = {
            'MATRIX_HOMESERVER_URL': 'https://matrix.test.org',
            'MATRIX_USER_ID': '@testbot:matrix.test.org', 
            'MATRIX_PASSWORD': 'test_password_123',
            'MATRIX_STORE_PATH': os.path.join(temp_dir, 'matrix_store'),
            'LLM_PROVIDER': 'openai',  # Not OpenRouter
            'LLM_API_KEY': 'test_openai_key_123',
            'LLM_MODEL': 'gpt-4',
            'OPENROUTER_PROVIDER': 'anthropic',  # Should be ignored
            'OPENROUTER_ROUTE': 'cheapest',  # Should be ignored
            'LOG_LEVEL': 'INFO'
        }
        
        # Set environment variables
        for key, value in test_env_vars.items():
            os.environ[key] = value
        
        try:
            config = Config()
            print("✓ OpenAI configuration loaded successfully")
            
            # Test that OpenRouter vars are loaded but not validated
            assert config.llm_provider == 'openai'
            assert config.openrouter_provider == 'anthropic'  # Still loaded
            assert config.openrouter_route == 'cheapest'  # Still loaded
            
            # Test that OpenRouter parameters are empty for non-OpenRouter providers
            params = config.get_openrouter_parameters()
            assert params == {}, f"Expected empty dict, got {params}"
            
            print("✓ OpenRouter parameters correctly ignored for OpenAI provider")
            
            return True
            
        except Exception as e:
            print(f"✗ Non-OpenRouter provider test failed: {e}")
            return False
        finally:
            # Clean up environment variables
            for key in test_env_vars.keys():
                if key in os.environ:
                    del os.environ[key]

def main():
    """Run all OpenRouter configuration tests."""
    print("Testing OpenRouter-specific configuration parameters...")
    print(f"Python path: {sys.path[0]}")
    print(f"Current directory: {os.getcwd()}")
    
    # Set up logging to capture any config logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run tests
    success = True
    
    success &= test_openrouter_defaults()
    success &= test_openrouter_custom_config()
    success &= test_openrouter_invalid_route()
    success &= test_non_openrouter_provider()
    
    if success:
        print("\n🎉 All OpenRouter configuration tests passed!")
        print("OpenRouter provider selection and routing parameters work correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some OpenRouter tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()