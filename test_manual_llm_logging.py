#!/usr/bin/env python3
"""
Manual verification test for LLM logging output.

This test creates a simulated environment to verify that LLM logging 
works correctly without needing actual API credentials.
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_llm_logging_output():
    """Test LLM logging with simulated responses."""
    print("=== Testing LLM Logging Output ===")
    
    # Set up test environment
    test_env = {
        'MATRIX_HOMESERVER_URL': 'https://matrix.test.org',
        'MATRIX_USER_ID': '@testbot:matrix.test.org', 
        'MATRIX_PASSWORD': 'test_password',
        'LLM_API_KEY': 'test_api_key',
        'LOG_LEVEL': 'LLM',
        'LLM_LOG_LEVEL': 'LLM',
        'EXCLUDE_MATRIX_NIO_LOGS': 'true'
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    try:
        from src.config import Config
        from src.logging_utils import configure_logging, get_llm_logger
        from src.llm import LLMClient
        from src.discourse import DiscourseSearcher, DiscoursePost
        
        # Configure logging to capture output
        log_capture = StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            # Configure logging
            configure_logging(
                log_level='LLM',
                logs_dir=temp_dir,
                exclude_matrix_nio=True
            )
            
            # Add string capture handler for verification
            handler = logging.StreamHandler(log_capture)
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            
            # Add to LLM logger
            llm_logger = get_llm_logger('src.llm')
            llm_logger.addHandler(handler)
            llm_logger.setLevel(logging.DEBUG)
            
            # Create configuration and mock dependencies
            config = Config()
            discourse_searcher = MagicMock(spec=DiscourseSearcher)
            
            # Mock discourse search results
            mock_post = DiscoursePost(
                id=123,
                title="Test Topic",
                excerpt="This is a test topic excerpt for verification.",
                url="https://discourse.test.org/t/test-topic/123",
                topic_id=123,
                category_id=1,
                tags=["help", "ubuntu"],
                created_at="2024-01-01T00:00:00Z",
                like_count=5,
                reply_count=3
            )
            discourse_searcher.search = AsyncMock(return_value=[mock_post])
            
            # Create LLM client
            llm_client = LLMClient(config, discourse_searcher)
            
            # Mock OpenAI client response
            mock_choice = MagicMock()
            mock_choice.finish_reason = 'tool_calls'
            mock_choice.message.content = None
            
            # Mock tool call
            mock_tool_call = MagicMock()
            mock_tool_call.id = "call_123"
            mock_tool_call.function.name = "search_discourse"
            mock_tool_call.function.arguments = json.dumps({"query": "test query"})
            mock_choice.message.tool_calls = [mock_tool_call]
            
            # Mock second response (send_link)
            mock_choice2 = MagicMock()
            mock_choice2.finish_reason = 'tool_calls'
            mock_choice2.message.content = None
            
            mock_tool_call2 = MagicMock()
            mock_tool_call2.id = "call_456"
            mock_tool_call2.function.name = "send_link"
            mock_tool_call2.function.arguments = json.dumps({
                "url": "https://discourse.test.org/t/test-topic/123",
                "message": "I found a relevant topic for your question"
            })
            mock_choice2.message.tool_calls = [mock_tool_call2]
            
            # Mock responses
            mock_response1 = MagicMock()
            mock_response1.choices = [mock_choice]
            mock_response1.usage.prompt_tokens = 150
            mock_response1.usage.completion_tokens = 25
            mock_response1.usage.total_tokens = 175
            
            mock_response2 = MagicMock()
            mock_response2.choices = [mock_choice2]
            mock_response2.usage.prompt_tokens = 200
            mock_response2.usage.completion_tokens = 30
            mock_response2.usage.total_tokens = 230
            
            # Mock the OpenAI client
            with patch('src.llm.AsyncOpenAI') as mock_openai:
                mock_client = AsyncMock()
                mock_client.chat.completions.create.side_effect = [mock_response1, mock_response2]
                mock_openai.return_value = mock_client
                
                # Recreate LLM client with mock
                llm_client = LLMClient(config, discourse_searcher)
                
                # Process a test question
                question = "How do I install Ubuntu?"
                result = await llm_client.process_question_with_tools(question)
                
                # Get captured log output
                log_output = log_capture.getvalue()
                
                print("✓ LLM processing completed")
                print(f"✓ Result: {result}")
                
                # Verify expected log messages are present
                expected_logs = [
                    "LLM: Processing question with tools:",
                    "LLM: System prompt length:",
                    "LLM: LLM attempt 1/3",
                    "LLM: Sending", "messages to LLM",
                    "LLM: LLM response received - finish_reason: tool_calls",
                    "LLM: LLM requested 1 tool call(s)",
                    "LLM: Executing function: search_discourse",
                    "LLM: Searching Discourse with query:",
                    "LLM: Discourse search returned 1 results",
                    "LLM: Executing function: send_link",
                    "LLM: LLM selected URL to send:",
                    "LLM: Final response prepared:",
                    "LLM: Token usage - prompt:",
                    "LLM: Question processing completed successfully"
                ]
                
                missing_logs = []
                for expected in expected_logs:
                    if expected not in log_output:
                        missing_logs.append(expected)
                
                if missing_logs:
                    print(f"❌ Missing expected log messages: {missing_logs}")
                    print(f"Actual log output:\n{log_output}")
                    return False
                
                print("✓ All expected LLM log messages found")
                
                # Show sample of actual log output
                print("\n=== Sample Log Output ===")
                log_lines = log_output.strip().split('\n')
                for line in log_lines[:10]:  # Show first 10 lines
                    print(line)
                if len(log_lines) > 10:
                    print(f"... and {len(log_lines) - 10} more lines")
                
                return True
                
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up environment
        for key in test_env.keys():
            if key in os.environ:
                del os.environ[key]


async def test_matrix_nio_filtering():
    """Test that matrix-nio logs are properly filtered."""
    print("\n=== Testing Matrix-nio Log Filtering ===")
    
    try:
        from src.logging_utils import configure_logging, MatrixNioFilter
        
        # Create log capture
        log_capture = StringIO()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Configure logging with matrix-nio filtering
            configure_logging(
                log_level='DEBUG',
                logs_dir=temp_dir,
                exclude_matrix_nio=True
            )
            
            # Create test loggers
            llm_logger = logging.getLogger('src.llm')
            nio_logger = logging.getLogger('nio.client')
            aiohttp_logger = logging.getLogger('aiohttp.access')
            
            # Add capture handler to root logger
            handler = logging.StreamHandler(log_capture)
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            
            root_logger = logging.getLogger()
            root_logger.addHandler(handler)
            
            # Test logging from different sources
            llm_logger.info("LLM test message - should appear")
            nio_logger.info("Matrix-nio test message - should be filtered")
            aiohttp_logger.info("Aiohttp test message - should be filtered")
            
            log_output = log_capture.getvalue()
            
            # Check filtering
            if "LLM test message - should appear" not in log_output:
                print("❌ LLM message was incorrectly filtered")
                return False
                
            if "Matrix-nio test message" in log_output:
                print("❌ Matrix-nio message was not filtered")
                return False
                
            if "Aiohttp test message" in log_output:
                print("❌ Aiohttp message was not filtered")
                return False
                
            print("✓ Matrix-nio filtering working correctly")
            return True
            
    except Exception as e:
        print(f"❌ Matrix-nio filtering test failed: {e}")
        return False


async def main():
    """Run all verification tests."""
    print("Manual verification of LLM logging functionality...\n")
    
    try:
        success = True
        success &= await test_llm_logging_output()
        success &= await test_matrix_nio_filtering()
        
        if success:
            print("\n=== All Verification Tests Passed! ===")
            print("✅ LLM logging outputs are working correctly")
            print("✅ Custom LLM log level is functioning properly")
            print("✅ Matrix-nio log filtering is working")
            print("✅ All expected log messages are being generated")
            
            print("\n=== Features Verified ===")
            print("1. LLM responses are logged at LLM level")
            print("2. Token usage information is logged")
            print("3. Function calls and results are logged")
            print("4. LLM decision process is visible in logs")
            print("5. Matrix-nio logs can be filtered out")
        else:
            print("\n❌ Some verification tests failed!")
            
        return success
        
    except Exception as e:
        print(f"\n❌ Unexpected error during verification: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)