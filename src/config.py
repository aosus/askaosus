import os
from typing import Optional
from urllib.parse import urlparse


class Config:
    """Configuration class for the Askaosus Matrix Bot."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Matrix configuration
        self.matrix_homeserver_url = self._get_required_env("MATRIX_HOMESERVER_URL")
        self.matrix_user_id = self._get_required_env("MATRIX_USER_ID")
        self.matrix_password = self._get_required_env("MATRIX_PASSWORD")
        self.matrix_device_name = os.getenv("MATRIX_DEVICE_NAME", "askaosus-python")
        self.matrix_store_path = os.getenv("MATRIX_STORE_PATH", "/app/data/matrix_store")
        
        # Discourse configuration
        self.discourse_base_url = os.getenv("DISCOURSE_BASE_URL", "https://discourse.aosus.org")
        self.discourse_api_key = os.getenv("DISCOURSE_API_KEY")
        self.discourse_username = os.getenv("DISCOURSE_USERNAME")
        
        # LLM configuration
        self.llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.llm_api_key = self._get_required_env("LLM_API_KEY")
        self.llm_base_url = os.getenv("LLM_BASE_URL")
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4")
        self.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "500"))
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        
        # Bot behavior configuration
        self.bot_rate_limit_seconds = float(os.getenv("BOT_RATE_LIMIT_SECONDS", "1.0"))
        self.bot_max_search_results = int(os.getenv("BOT_MAX_SEARCH_RESULTS", "5"))
        self.bot_debug = os.getenv("BOT_DEBUG", "false").lower() == "true"
        
        # Logging configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        
        # Validate configuration
        self._validate()
    
    def _get_required_env(self, key: str) -> str:
        """Get a required environment variable."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} not set")
        return value
    
    def _validate(self):
        """Validate configuration values."""
        # Validate Matrix homeserver URL
        parsed = urlparse(self.matrix_homeserver_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid MATRIX_HOMESERVER_URL")
        
        # Validate LLM provider
        valid_providers = {"openai", "openrouter", "gemini"}
        if self.llm_provider not in valid_providers:
            raise ValueError(f"Invalid LLM_PROVIDER. Must be one of: {valid_providers}")
        
        # Set default base URLs for providers if not specified
        if not self.llm_base_url:
            if self.llm_provider == "openai":
                self.llm_base_url = "https://api.openai.com/v1"
            elif self.llm_provider == "openrouter":
                self.llm_base_url = "https://openrouter.ai/api/v1"
            elif self.llm_provider == "gemini":
                self.llm_base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        # Validate Discourse URL
        parsed = urlparse(self.discourse_base_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid DISCOURSE_BASE_URL")
        
        # Log configuration (without sensitive data)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Configuration loaded:")
        logger.info(f"  Matrix homeserver: {self.matrix_homeserver_url}")
        logger.info(f"  Matrix user: {self.matrix_user_id}")
        logger.info(f"  Discourse URL: {self.discourse_base_url}")
        logger.info(f"  LLM provider: {self.llm_provider}")
        logger.info(f"  LLM base URL: {self.llm_base_url}")
        logger.info(f"  LLM model: {self.llm_model}")
        logger.info(f"  Bot debug mode: {self.bot_debug}")
        logger.info(f"  Log level: {self.log_level}")
    
    def get_openai_client_kwargs(self) -> dict:
        """Get kwargs for OpenAI client initialization."""
        kwargs = {
            "api_key": self.llm_api_key,
            "base_url": self.llm_base_url,
        }
        
        # Add provider-specific headers
        if self.llm_provider == "openrouter":
            kwargs["default_headers"] = {
                "HTTP-Referer": "https://github.com/aosus/askaosus",
                "X-Title": "Askaosus Matrix Bot",
            }
        
        return kwargs
