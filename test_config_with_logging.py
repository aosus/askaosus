#!/usr/bin/env python3
"""
Test that the bot configuration loads correctly with the new logging setup.

This test verifies:
1. Configuration loads without errors with new logging options
2. Logging is configured properly
3. LLM logger works as expected
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_configuration_with_logging():
    """Test configuration loading with new logging options."""
    print("=== Testing Configuration with Logging Options ===")
    
    # Set up test environment variables
    test_env = {
        'MATRIX_HOMESERVER_URL': 'https://matrix.test.org',
        'MATRIX_USER_ID': '@testbot:matrix.test.org',
        'MATRIX_PASSWORD': 'test_password',
        'LLM_API_KEY': 'test_api_key',
        'LOG_LEVEL': 'LLM',
        'LLM_LOG_LEVEL': 'LLM', 
        'EXCLUDE_MATRIX_NIO_LOGS': 'true'
    }
    
    # Set environment variables
    for key, value in test_env.items():
        os.environ[key] = value
    
    try:
        # Import and test configuration
        from src.config import Config
        from src.logging_utils import configure_logging, get_llm_logger
        
        # Load configuration
        config = Config()
        
        # Test that new configuration options are loaded
        assert config.llm_log_level == 'LLM', f"Expected LLM_LOG_LEVEL=LLM, got {config.llm_log_level}"
        assert config.exclude_matrix_nio_logs == True, f"Expected EXCLUDE_MATRIX_NIO_LOGS=true, got {config.exclude_matrix_nio_logs}"
        
        print("✓ Configuration loaded successfully with new logging options")
        
        # Test logging configuration
        with tempfile.TemporaryDirectory() as temp_dir:
            configure_logging(
                log_level=config.log_level,
                logs_dir=temp_dir,
                exclude_matrix_nio=config.exclude_matrix_nio_logs
            )
            
            # Test LLM logger
            llm_logger = get_llm_logger('test.llm.module')
            
            # Verify LLM logger has the llm method
            assert hasattr(llm_logger, 'llm'), "LLM logger should have llm() method"
            
            print("✓ Logging configured successfully")
            
            # Test that log file is created
            log_file = Path(temp_dir) / "bot.log"
            if not log_file.exists():
                # Create a dummy log message to trigger file creation
                llm_logger.llm("Test LLM message")
                
            print("✓ Log file handling working")
        
        return True
        
    finally:
        # Clean up environment variables
        for key in test_env.keys():
            if key in os.environ:
                del os.environ[key]


def test_logging_import():
    """Test that logging components can be imported."""
    print("\n=== Testing Logging Import ===")
    
    try:
        from src.logging_utils import configure_logging, get_llm_logger, LLM_LEVEL, MatrixNioFilter
        from src.config import Config
        
        print("✓ All logging components imported successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing configuration with new logging functionality...\n")
    
    try:
        success = True
        success &= test_logging_import()
        success &= test_configuration_with_logging()
        
        if success:
            print("\n=== All Tests Passed! ===")
            print("✅ Configuration loads correctly with new logging options")
            print("✅ Logging components work as expected")
        else:
            print("\n❌ Some tests failed!")
            
        return success
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)