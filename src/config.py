import os
from typing import Optional
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse


class Config:
    """Configuration class for the Askaosus Matrix Bot."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Matrix configuration
        self.matrix_homeserver_url = self._get_required_env("MATRIX_HOMESERVER_URL")
        self.matrix_user_id = self._get_required_env("MATRIX_USER_ID")
        self.matrix_password = self._get_required_env("MATRIX_PASSWORD")
        self.matrix_device_name = os.getenv("MATRIX_DEVICE_NAME", "askaosus-python")
        # Default to local data directory for session persistence in dev
        default_store = os.path.join(os.getcwd(), "data", "matrix_store")
        self.matrix_store_path = os.getenv("MATRIX_STORE_PATH", default_store)
        
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
        
        # OpenRouter specific configuration
        self.openrouter_provider = os.getenv("OPENROUTER_PROVIDER", "").strip()
        self.openrouter_route = os.getenv("OPENROUTER_ROUTE", "best").lower().strip()
        
        # Bot behavior configuration
        # Bot mentions (comma-separated list)
        bot_mentions_str = os.getenv("BOT_MENTIONS", "@askaosus,askaosus")
        self.bot_mentions = [mention.strip() for mention in bot_mentions_str.split(",")]
        self.bot_rate_limit_seconds = float(os.getenv("BOT_RATE_LIMIT_SECONDS", "1.0"))
        self.bot_max_search_results = int(os.getenv("BOT_MAX_SEARCH_RESULTS", "5"))
        self.bot_max_search_iterations = int(os.getenv("BOT_MAX_SEARCH_ITERATIONS", "3"))
        self.bot_debug = os.getenv("BOT_DEBUG", "false").lower() == "true"
        
        # UTM tracking configuration
        self.utm_tags = os.getenv("BOT_UTM_TAGS", "")
        
        # Logging configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.llm_log_level = os.getenv("LLM_LOG_LEVEL", "LLM").upper()
        self.exclude_matrix_nio_logs = os.getenv("EXCLUDE_MATRIX_NIO_LOGS", "false").lower() == "true"
        
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
        
        # Validate OpenRouter route if specified
        if self.llm_provider == "openrouter" and self.openrouter_route:
            valid_routes = {"best", "cheapest", "fastest"}
            if self.openrouter_route not in valid_routes:
                raise ValueError(f"Invalid OPENROUTER_ROUTE. Must be one of: {valid_routes}")
        
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
        if self.llm_provider == "openrouter":
            logger.info(f"  OpenRouter provider: {self.openrouter_provider or 'auto'}")
            logger.info(f"  OpenRouter route: {self.openrouter_route}")
        logger.info(f"  Bot debug mode: {self.bot_debug}")
        logger.info(f"  UTM tags configured: {'Yes' if self.utm_tags else 'No'}")
        logger.info(f"  Log level: {self.log_level}")
        logger.info(f"  LLM log level: {self.llm_log_level}")
        logger.info(f"  Exclude matrix-nio logs: {self.exclude_matrix_nio_logs}")
    
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
    
    def get_openrouter_parameters(self) -> dict:
        """Get OpenRouter-specific parameters for chat completion requests."""
        if self.llm_provider != "openrouter":
            return {}
        
        params = {}
        
        # Add provider selection if specified
        if self.openrouter_provider:
            params["provider"] = {"require": [self.openrouter_provider]}
        
        # Add route preference if specified
        if self.openrouter_route and self.openrouter_route in {"best", "cheapest", "fastest"}:
            params["route"] = self.openrouter_route
        
        return params
    
    def add_utm_tags_to_url(self, url: str) -> str:
        """Add UTM tags to a URL if configured."""
        if not self.utm_tags:
            return url
        
        try:
            # Parse the URL
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            # Parse UTM tags from environment variable
            # Expected format: "utm_source=bot&utm_medium=matrix&utm_campaign=help"
            utm_params = {}
            for param in self.utm_tags.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    utm_params[key] = [value]
            
            # Add UTM parameters to existing query parameters
            query_params.update(utm_params)
            
            # Build the new URL with UTM tags
            new_query = urlencode(query_params, doseq=True)
            new_parsed_url = parsed_url._replace(query=new_query)
            
            return urlunparse(new_parsed_url)
        except Exception as e:
            # If there's any error adding UTM tags, return the original URL
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to add UTM tags to URL {url}: {e}")
            return url
