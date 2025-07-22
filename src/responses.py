import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ResponseConfig:
    """Manages configurable responses for the bot."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the response configuration."""
        if config_path is None:
            # Try different locations in order of preference
            possible_paths = [
                "/app/responses.json",  # Production Docker path
                "responses.json",  # Development path (current directory)
                os.path.join(os.path.dirname(__file__), "..", "responses.json"),  # Relative to src/
            ]
            
            self.config_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    self.config_path = path
                    break
            
            if not self.config_path:
                self.config_path = possible_paths[0]  # Default to production path
        else:
            self.config_path = config_path
            
        self.responses = self._load_responses()
    
    def _load_responses(self) -> Dict[str, Any]:
        """Load responses from the configuration file."""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"Response config file not found at {self.config_path}, using defaults")
                return self._get_default_responses()
        except Exception as e:
            logger.error(f"Error loading response config: {e}, using defaults")
            return self._get_default_responses()
    
    def _get_default_responses(self) -> Dict[str, Any]:
        """Get default hardcoded responses as fallback."""
        return {
            "error_messages": {
                "rate_limit_error": "The forum is currently receiving too many requests. Please try again in a few moments.",
                "discourse_unreachable": "The forum is currently unreachable. Please try again later or visit the forum directly: https://discourse.aosus.org",
                "llm_down": "The AI assistant is currently unavailable. Please try again later or visit the forum directly: https://discourse.aosus.org"
            },
            "discourse_messages": {
                "no_results": "No relevant topics found.",
                "untitled_post": "Untitled post",
                "untitled_topic": "Untitled topic",
                "default_excerpt": "Topic in Aosus community"
            }
        }
    
    def get_response(self, category: str, key: str) -> str:
        """
        Get a response message.
        
        Args:
            category: Response category (error_messages, discourse_messages, etc.)
            key: Specific response key
            
        Returns:
            The response message, falling back to a generic error message if not found
        """
        try:
            category_responses = self.responses.get(category, {})
            message = category_responses.get(key)
            
            if message:
                return message
            else:
                # Final fallback to a generic message
                return "Sorry, an unexpected error occurred"
                
        except Exception as e:
            logger.error(f"Error getting response {category}.{key}: {e}")
            return "Sorry, an unexpected error occurred"
    
    def get_error_message(self, error_type: str) -> str:
        """Get an error message."""
        return self.get_response("error_messages", error_type)
    
    def get_discourse_message(self, message_type: str) -> str:
        """Get a discourse-related message.""" 
        return self.get_response("discourse_messages", message_type)