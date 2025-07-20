# Environment Variable Testing

This document explains how environment variables are handled in the Askaosus Matrix Bot Docker deployment and how to verify they work correctly without requiring a `.env` file.

## Overview

The bot is designed to work with environment variables passed directly through Docker, either via `docker run -e` flags or through Docker Compose's `environment` section. **No `.env` file is required in production.**

## Environment Variable Sources

1. **Docker Run**: Variables passed with `-e` flags
2. **Docker Compose**: Variables defined in the `environment` section
3. **Host Environment**: Variables available in the shell when running docker-compose
4. **`.env` file** (optional, for development only)

## Testing Environment Variable Configuration

### Quick Test

Run the environment configuration test:

```bash
python test_env_config.py
```

This test verifies:
- ✅ Configuration loads correctly from environment variables
- ✅ Default values are applied for optional variables
- ✅ No `.env` file is required (`load_dotenv` works without it)
- ✅ All required configuration values are validated

### Docker Container Test

Test with a Docker container using environment variables only:

```bash
docker run --rm \
  -e MATRIX_HOMESERVER_URL=https://matrix.test.org \
  -e MATRIX_USER_ID=@testbot:matrix.test.org \
  -e MATRIX_PASSWORD=test_password_123 \
  -e DISCOURSE_API_KEY=test_key \
  -e DISCOURSE_USERNAME=testuser \
  -e LLM_API_KEY=test_llm_key \
  -e BOT_DEBUG=true \
  ghcr.io/aosus/askaosus:latest
```

### Docker Compose Test

Test with the provided test configuration:

```bash
# Remove any .env file to ensure we're testing without it
rm -f .env

# Test that docker-compose works with environment variables only
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

## Environment Variable Configuration

### Required Variables

These variables **must** be set for the bot to start:

- `MATRIX_HOMESERVER_URL`: Matrix homeserver URL
- `MATRIX_USER_ID`: Bot's Matrix user ID
- `MATRIX_PASSWORD`: Bot's Matrix password
- `LLM_API_KEY`: API key for the LLM provider

### Optional Variables (with defaults)

These variables have sensible defaults but can be overridden:

| Variable | Default | Description |
|----------|---------|-------------|
| `MATRIX_DEVICE_NAME` | `askaosus-python` | Device name for Matrix login |
| `MATRIX_STORE_PATH` | `/app/data/matrix_store` | Path for Matrix session storage |
| `DISCOURSE_BASE_URL` | `https://discourse.aosus.org` | Discourse forum URL |
| `LLM_PROVIDER` | `openai` | LLM provider (openai/openrouter/gemini) |
| `LLM_MODEL` | `gpt-4` | LLM model to use |
| `LLM_MAX_TOKENS` | `500` | Maximum tokens for LLM responses |
| `LLM_TEMPERATURE` | `0.7` | LLM temperature setting |
| `BOT_RATE_LIMIT_SECONDS` | `1.0` | Rate limiting between messages |
| `BOT_MAX_SEARCH_RESULTS` | `5` | Maximum search results to return |
| `BOT_MAX_SEARCH_ITERATIONS` | `3` | Maximum search iterations |
| `BOT_DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |

## How It Works

1. **Main Entry Point** (`src/main.py`):
   ```python
   from dotenv import load_dotenv
   load_dotenv(override=False)  # Won't override existing env vars
   ```
   
2. **Configuration Loading** (`src/config.py`):
   ```python
   def __init__(self):
       self.matrix_homeserver_url = self._get_required_env("MATRIX_HOMESERVER_URL")
       self.matrix_user_id = self._get_required_env("MATRIX_USER_ID")
       # ... loads all config from os.getenv()
   ```

3. **Docker Compose** (`docker-compose.yml`):
   ```yaml
   environment:
     - MATRIX_HOMESERVER_URL=${MATRIX_HOMESERVER_URL:-https://matrix.org}
     - MATRIX_USER_ID=${MATRIX_USER_ID:-@askaosus:matrix.org}
     # ... uses variable substitution
   ```

## Key Benefits

- **No file mounting required**: Variables passed directly through Docker
- **Secure**: No sensitive data in version control
- **Flexible**: Works with any container orchestration system
- **Backward compatible**: Still works with `.env` files for development
- **Testable**: Comprehensive tests ensure it works correctly

## Troubleshooting

### Bot won't start - missing environment variables

Check that all required variables are set:
```bash
docker run --rm your-image python -c "from src.config import Config; Config()"
```

### Variables not being loaded

1. Verify variables are available in the container:
   ```bash
   docker run --rm your-image env | grep MATRIX
   ```

2. Check Docker Compose variable substitution:
   ```bash
   docker compose config
   ```

3. Ensure no conflicting `.env` file in Docker context

### Values not matching expectations

The bot logs its configuration on startup (without sensitive values):
```
INFO - Configuration loaded:
INFO -   Matrix homeserver: https://matrix.org
INFO -   Matrix user: @askaosus:matrix.org
...
```

Check the logs to verify configuration values are correct.