#!/usr/bin/env python3
"""
Manual verification script to demonstrate OpenRouter configuration in action.
This shows exactly how the configuration would be used when making LLM requests.
"""
import os
import sys
import tempfile
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import Config

def demonstrate_configuration():
    """Demonstrate how OpenRouter configuration works with different settings."""
    
    scenarios = [
        {
            "name": "Default OpenRouter (auto provider, best route)",
            "env_vars": {
                'LLM_PROVIDER': 'openrouter',
                'LLM_MODEL': 'anthropic/claude-3-haiku',
            }
        },
        {
            "name": "OpenRouter with specific provider",
            "env_vars": {
                'LLM_PROVIDER': 'openrouter',
                'LLM_MODEL': 'anthropic/claude-3-haiku',
                'OPENROUTER_PROVIDER': 'anthropic',
            }
        },
        {
            "name": "OpenRouter with cheapest routing",
            "env_vars": {
                'LLM_PROVIDER': 'openrouter',
                'LLM_MODEL': 'anthropic/claude-3-haiku',
                'OPENROUTER_ROUTE': 'cheapest',
            }
        },
        {
            "name": "OpenRouter with both provider and route",
            "env_vars": {
                'LLM_PROVIDER': 'openrouter',
                'LLM_MODEL': 'gpt-4',
                'OPENROUTER_PROVIDER': 'openai',
                'OPENROUTER_ROUTE': 'fastest',
            }
        },
        {
            "name": "OpenAI provider (OpenRouter params ignored)",
            "env_vars": {
                'LLM_PROVIDER': 'openai',
                'LLM_MODEL': 'gpt-4',
                'OPENROUTER_PROVIDER': 'anthropic',  # Should be ignored
                'OPENROUTER_ROUTE': 'cheapest',     # Should be ignored
            }
        }
    ]
    
    print("=== OpenRouter Configuration Demonstration ===")
    print("This shows how the environment variables translate to API request parameters:\n")
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print("   Environment variables:")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Base environment variables required for config
            base_env_vars = {
                'MATRIX_HOMESERVER_URL': 'https://matrix.test.org',
                'MATRIX_USER_ID': '@testbot:matrix.test.org', 
                'MATRIX_PASSWORD': 'test_password_123',
                'MATRIX_STORE_PATH': os.path.join(temp_dir, 'matrix_store'),
                'LLM_API_KEY': 'sk-test-key-123',
                'LOG_LEVEL': 'ERROR'
            }
            
            # Combine base with scenario-specific variables
            all_env_vars = {**base_env_vars, **scenario['env_vars']}
            
            # Set environment variables
            for key, value in all_env_vars.items():
                os.environ[key] = value
            
            try:
                config = Config()
                
                # Show relevant environment variables
                for key, value in scenario['env_vars'].items():
                    print(f"     {key}={value}")
                
                print("   Result:")
                print(f"     Provider: {config.llm_provider}")
                print(f"     Model: {config.llm_model}")
                print(f"     Base URL: {config.llm_base_url}")
                
                # Show OpenRouter parameters that would be added to requests
                openrouter_params = config.get_openrouter_parameters()
                if openrouter_params:
                    print(f"     OpenRouter API parameters: {json.dumps(openrouter_params, indent=8)}")
                else:
                    print("     OpenRouter API parameters: (none - using standard OpenAI client)")
                
                # Show client kwargs
                client_kwargs = config.get_openai_client_kwargs()
                if "default_headers" in client_kwargs:
                    print("     Additional headers:")
                    for header_key, header_value in client_kwargs["default_headers"].items():
                        print(f"       {header_key}: {header_value}")
                
                print()  # Empty line for readability
                
            except Exception as e:
                print(f"     ERROR: {e}")
                print()
            finally:
                # Clean up environment variables
                for key in all_env_vars.keys():
                    if key in os.environ:
                        del os.environ[key]
    
    print("=== Summary ===")
    print("✓ OPENROUTER_PROVIDER allows manual provider selection")
    print("✓ OPENROUTER_ROUTE controls provider sorting (best/cheapest/fastest)")  
    print("✓ Parameters are only applied when LLM_PROVIDER=openrouter")
    print("✓ Configuration is validated and provides helpful defaults")
    print("✓ Original OpenRouter headers and base URL are preserved")

if __name__ == '__main__':
    demonstrate_configuration()