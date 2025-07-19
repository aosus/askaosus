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
                "no_results_found": {
                    "ar": "عذراً، لم أتمكن من العثور على موضوعات ذات صلة بسؤالك. يرجى المحاولة بصيغة مختلفة أو زيارة المنتدى مباشرة: https://discourse.aosus.org",
                    "en": "Sorry, I couldn't find any relevant topics for your question. Please try rephrasing your query or visit the forum directly: https://discourse.aosus.org"
                },
                "processing_error": {
                    "ar": "عذراً، حدث خطأ أثناء معالجة سؤالك. يرجى المحاولة مرة أخرى أو زيارة المنتدى مباشرة: https://discourse.aosus.org",
                    "en": "Sorry, an error occurred while processing your question. Please try again later or visit the forum directly: https://discourse.aosus.org"
                },
                "search_error": {
                    "ar": "عذراً، حدث خطأ أثناء البحث. يرجى المحاولة مرة أخرى أو زيارة المنتدى مباشرة: https://discourse.aosus.org",
                    "en": "Sorry, an error occurred while searching for an answer. Please try again later or visit the forum directly: https://discourse.aosus.org"
                },
                "fallback_error": {
                    "ar": "عذراً، لم أتمكن من معالجة سؤالك. يرجى المحاولة مرة أخرى أو زيارة المنتدى مباشرة: https://discourse.aosus.org",
                    "en": "Sorry, I couldn't process your question. Please try again or visit the forum directly: https://discourse.aosus.org"
                }
            },
            "discourse_messages": {
                "no_results": {
                    "ar": "لم يتم العثور على موضوعات ذات صلة.",
                    "en": "No relevant topics found."
                },
                "untitled_post": {
                    "ar": "منشور بدون عنوان",
                    "en": "Untitled post"
                },
                "untitled_topic": {
                    "ar": "موضوع بدون عنوان", 
                    "en": "Untitled topic"
                },
                "default_excerpt": {
                    "ar": "موضوع في مجتمع أسس",
                    "en": "Topic in Aosus community"
                }
            },
            "system_messages": {
                "perfect_match": {
                    "ar": "وجدت تطابقاً مثالياً لسؤالك:",
                    "en": "I found a perfect match for your question:"
                },
                "closest_match": {
                    "ar": "إليك أقرب موضوع ذي صلة وجدته:",
                    "en": "Here's the closest relevant topic I found:"
                }
            }
        }
    
    def get_response(self, category: str, key: str, language: str = "ar") -> str:
        """
        Get a response message.
        
        Args:
            category: Response category (error_messages, discourse_messages, etc.)
            key: Specific response key
            language: Language code (ar, en)
            
        Returns:
            The response message in the requested language, falling back to Arabic
        """
        try:
            category_responses = self.responses.get(category, {})
            message_variants = category_responses.get(key, {})
            
            # Try requested language first, then fall back to Arabic, then English
            if language in message_variants:
                return message_variants[language]
            elif "ar" in message_variants:
                return message_variants["ar"]  
            elif "en" in message_variants:
                return message_variants["en"]
            else:
                # Final fallback to a generic message
                return "عذراً، حدث خطأ غير متوقع"
                
        except Exception as e:
            logger.error(f"Error getting response {category}.{key}.{language}: {e}")
            return "عذراً، حدث خطأ غير متوقع"
    
    def get_error_message(self, error_type: str, language: str = "ar") -> str:
        """Get an error message."""
        return self.get_response("error_messages", error_type, language)
    
    def get_discourse_message(self, message_type: str, language: str = "ar") -> str:
        """Get a discourse-related message.""" 
        return self.get_response("discourse_messages", message_type, language)
        
    def get_system_message(self, message_type: str, language: str = "ar") -> str:
        """Get a system message."""
        return self.get_response("system_messages", message_type, language)