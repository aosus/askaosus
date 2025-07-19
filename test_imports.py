#!/usr/bin/env python3
"""
Integration test to verify imports work correctly after changes.
"""
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all imports work correctly after our changes."""
    print("Testing imports...")
    
    try:
        # Test responses module
        print("✓ Importing responses module...")
        from responses import ResponseConfig
        
        # Test updated modules import correctly
        print("✓ Importing config module...")
        from config import Config
        
        print("✓ Importing discourse module...")
        from discourse import DiscourseSearcher
        
        print("✓ Importing llm module...")
        from llm import LLMClient
        
        print("✓ Importing bot module...")
        from bot import AskaosusBot
        
        print("✓ All imports successful!")
        
        # Test that classes can be instantiated (with mock config)
        print("✓ Testing ResponseConfig instantiation...")
        response_config = ResponseConfig()
        test_message = response_config.get_error_message("no_results_found", "en")
        print(f"  Sample message: {test_message[:50]}...")
        
        print("🎉 All import tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_imports():
        sys.exit(0)
    else:
        sys.exit(1)