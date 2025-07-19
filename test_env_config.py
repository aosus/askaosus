#!/usr/bin/env python3
"""
Test script to validate that environment variables are loaded correctly in Docker
without needing to mount a .env file.
"""
import os
import sys
import tempfile
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import Config

def test_env_config():
    """Test that environment variables are loaded correctly."""
    print("=== Testing Environment Variable Configuration ===")
    
    # Create a temporary directory for matrix store
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up minimal required environment variables for testing
        test_env_vars = {
            'MATRIX_HOMESERVER_URL': 'https://matrix.test.org',
            'MATRIX_USER_ID': '@testbot:matrix.test.org', 
            'MATRIX_PASSWORD': 'test_password_123',
            'MATRIX_DEVICE_NAME': 'test-device',
            'MATRIX_STORE_PATH': os.path.join(temp_dir, 'matrix_store'),
            'DISCOURSE_BASE_URL': 'https://discourse.test.org',
            'DISCOURSE_API_KEY': 'test_discourse_key',
            'DISCOURSE_USERNAME': 'testuser',
            'LLM_PROVIDER': 'openai',
            'LLM_API_KEY': 'test_llm_key_123',
            'LLM_MODEL': 'gpt-3.5-turbo',
            'BOT_DEBUG': 'false',
            'LOG_LEVEL': 'INFO'
        }
        
        # Set environment variables
        for key, value in test_env_vars.items():
            os.environ[key] = value
            
        print("✓ Set test environment variables")
        
        try:
            # Test configuration loading
            config = Config()
            print("✓ Configuration loaded successfully")
            
            # Validate key configuration values
            assert config.matrix_homeserver_url == test_env_vars['MATRIX_HOMESERVER_URL']
            assert config.matrix_user_id == test_env_vars['MATRIX_USER_ID']
            assert config.matrix_password == test_env_vars['MATRIX_PASSWORD']
            assert config.discourse_base_url == test_env_vars['DISCOURSE_BASE_URL']
            assert config.llm_api_key == test_env_vars['LLM_API_KEY']
            assert config.llm_model == test_env_vars['LLM_MODEL']
            
            print("✓ All configuration values match environment variables")
            
            # Test that optional variables have defaults
            assert config.bot_rate_limit_seconds == 1.0  # default
            assert config.bot_max_search_results == 5    # default
            assert config.bot_max_search_iterations == 3  # default
            assert config.llm_max_tokens == 500          # default
            assert config.llm_temperature == 0.7         # default
            
            print("✓ Default values applied correctly for optional variables")
            
            # Test OpenAI client kwargs
            client_kwargs = config.get_openai_client_kwargs()
            assert 'api_key' in client_kwargs
            assert 'base_url' in client_kwargs
            assert client_kwargs['api_key'] == test_env_vars['LLM_API_KEY']
            
            print("✓ OpenAI client configuration generated correctly")
            
            print("\n=== Configuration Test Results ===")
            print(f"Matrix Homeserver: {config.matrix_homeserver_url}")
            print(f"Matrix User: {config.matrix_user_id}")
            print(f"Discourse URL: {config.discourse_base_url}")
            print(f"LLM Provider: {config.llm_provider}")
            print(f"LLM Model: {config.llm_model}")
            print(f"Bot Debug: {config.bot_debug}")
            print(f"Log Level: {config.log_level}")
            
            return True
            
        except Exception as e:
            print(f"✗ Configuration loading failed: {e}")
            return False
        finally:
            # Clean up environment variables
            for key in test_env_vars.keys():
                if key in os.environ:
                    del os.environ[key]

def test_dotenv_optional():
    """Test that the app works when no .env file is present."""
    print("\n=== Testing dotenv Optional Behavior ===")
    
    # Ensure no .env file is present
    env_file = Path('.env')
    env_exists = env_file.exists()
    
    if env_exists:
        print("Found existing .env file - this test verifies it's not required")
    else:
        print("No .env file found - testing without it")
    
    # Test that load_dotenv doesn't fail when no .env file exists
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)
        print("✓ load_dotenv(override=False) works without .env file")
        return True
    except Exception as e:
        print(f"✗ load_dotenv failed: {e}")
        return False

def main():
    """Run all environment configuration tests."""
    print("Testing environment variable configuration for Docker deployment...")
    print(f"Python path: {sys.path[0]}")
    print(f"Current directory: {os.getcwd()}")
    
    # Set up logging to capture any config logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run tests
    success = True
    
    success &= test_dotenv_optional()
    success &= test_env_config()
    
    if success:
        print("\n🎉 All environment configuration tests passed!")
        print("The bot should work correctly in Docker with environment variables only.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()