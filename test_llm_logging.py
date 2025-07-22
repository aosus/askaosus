#!/usr/bin/env python3
"""
Test the custom LLM logging functionality.

This test verifies that:
1. The custom LLM log level is working correctly
2. LLM logs are properly formatted and filtered
3. Matrix-nio logs can be excluded when needed
"""

import logging
import os
import sys
import tempfile
from io import StringIO
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.logging_utils import configure_logging, get_llm_logger, LLM_LEVEL, MatrixNioFilter


def test_custom_llm_log_level():
    """Test that the custom LLM log level is working."""
    print("=== Testing Custom LLM Log Level ===")
    
    # Create a temporary log directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Configure logging
        configure_logging(log_level='DEBUG', logs_dir=temp_dir, exclude_matrix_nio=False)
        
        # Get an LLM logger
        llm_logger = get_llm_logger('test_llm')
        
        # Test that LLM level is available
        assert hasattr(llm_logger, 'llm'), "Logger should have llm() method"
        assert hasattr(logging, 'LLM'), "Logging module should have LLM level"
        assert logging.LLM == LLM_LEVEL, f"LLM level should be {LLM_LEVEL}"
        
        print(f"✓ Custom LLM log level created successfully at level {LLM_LEVEL}")
        
        # Test logging at different levels
        with StringIO() as log_capture:
            handler = logging.StreamHandler(log_capture)
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            
            test_logger = logging.getLogger('test_output')
            test_logger.setLevel(logging.DEBUG)
            test_logger.addHandler(handler)
            
            # Log at different levels
            test_logger.debug("Debug message")
            test_logger.info("Info message")
            test_logger.llm("LLM message")
            test_logger.warning("Warning message")
            
            log_output = log_capture.getvalue()
            
        # Check that all levels are present
        assert "DEBUG: Debug message" in log_output, "Debug message should be present"
        assert "INFO: Info message" in log_output, "Info message should be present"
        assert "LLM: LLM message" in log_output, "LLM message should be present"
        assert "WARNING: Warning message" in log_output, "Warning message should be present"
        
        print("✓ All log levels working correctly")
        
        # Test that log file is created
        log_file = Path(temp_dir) / "bot.log"
        assert log_file.exists(), "Log file should be created"
        
        print("✓ Log file creation working")
        

def test_matrix_nio_filtering():
    """Test that matrix-nio logs can be filtered out."""
    print("\n=== Testing Matrix-nio Log Filtering ===")
    
    # Create a filter
    nio_filter = MatrixNioFilter()
    
    # Create test log records
    class MockRecord:
        def __init__(self, name):
            self.name = name
    
    # Test records that should be filtered
    filtered_records = [
        MockRecord('nio.client'),
        MockRecord('nio.api'),
        MockRecord('aiohttp.client'),
        MockRecord('urllib3.connectionpool'),
    ]
    
    # Test records that should pass
    passing_records = [
        MockRecord('src.llm'),
        MockRecord('src.bot'),
        MockRecord('src.main'),
        MockRecord('custom.module'),
    ]
    
    # Test filtering
    for record in filtered_records:
        assert not nio_filter.filter(record), f"Record {record.name} should be filtered"
    
    for record in passing_records:
        assert nio_filter.filter(record), f"Record {record.name} should pass"
    
    print("✓ Matrix-nio filtering working correctly")


def test_log_level_configuration():
    """Test different log level configurations."""
    print("\n=== Testing Log Level Configuration ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test LLM level configuration
        configure_logging(log_level='LLM', logs_dir=temp_dir)
        
        root_logger = logging.getLogger()
        assert root_logger.level == LLM_LEVEL, f"Root logger level should be {LLM_LEVEL}"
        
        print("✓ LLM log level configuration working")
        
        # Test INFO level (should still show LLM logs)
        configure_logging(log_level='INFO', logs_dir=temp_dir)
        llm_logger = logging.getLogger('src.llm')
        
        # LLM logger should be configured to show LLM level logs
        assert llm_logger.level <= LLM_LEVEL, "LLM logger should show LLM level logs"
        
        print("✓ Mixed log level configuration working")


def test_llm_logger_functionality():
    """Test the get_llm_logger function."""
    print("\n=== Testing LLM Logger Functionality ===")
    
    # Get LLM logger
    logger = get_llm_logger('test_module')
    
    # Test that it has LLM method
    assert hasattr(logger, 'llm'), "LLM logger should have llm() method"
    
    # Test logging (capture to string)
    with StringIO() as log_capture:
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        # Test LLM logging
        logger.llm("Test LLM message")
        log_output = log_capture.getvalue()
        
        # Remove handler to avoid duplicate logs
        logger.removeHandler(handler)
    
    assert "test_module - LLM - Test LLM message" in log_output, "LLM message should be logged correctly"
    print("✓ LLM logger functionality working")


def main():
    """Run all tests."""
    print("Testing LLM logging functionality...\n")
    
    try:
        test_custom_llm_log_level()
        test_matrix_nio_filtering()
        test_log_level_configuration()
        test_llm_logger_functionality()
        
        print("\n=== All Tests Passed! ===")
        print("✅ Custom LLM log level is working correctly")
        print("✅ Matrix-nio filtering is working correctly") 
        print("✅ Log level configuration is working correctly")
        print("✅ LLM logger functionality is working correctly")
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)