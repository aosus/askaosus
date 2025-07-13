# Askaosus Matrix Bot

A Python Matrix bot that searches the Aosus Discourse forum to answer Arabic questions about free and open source software.

## Features

- Responds to mentions (`@askaosus` or `askaosus`)
- Searches Discourse forum posts to find relevant answers
- Supports multiple LLM providers (OpenAI, OpenRouter, Gemini)
- Configurable through environment variables
- Dockerized for easy deployment
- Stateless design with persistent Matrix session

## Setup

1. Copy `.env.example` to `.env` and configure your settings
2. Start the bot with Docker Compose:

   ```bash
   docker compose up -d
   ```

## Development

For development with hot reloading (no Docker needed):

```bash
# Install dependencies including dev support
pip install -r requirements.txt
# Run the bot with auto-reload on file changes
python dev.py
```

## How It Works

The bot operates as follows:

1. **Listening**: Monitors Matrix rooms for messages mentioning `@askaosus` or `askaosus`
2. **Question Detection**: Extracts the question from the message or reply
3. **Discourse Search**: Searches the Aosus Discourse forum for relevant posts
4. **AI Processing**: Uses the configured LLM to generate a helpful answer based on forum content
5. **Response**: Sends a concise Arabic response with links to relevant forum posts

### Bot Triggers

The bot responds to:

- Direct mentions: `@askaosus كيف أثبت برنامج على أوبونتو؟`
- Name mentions: `askaosus ما هو أفضل محرر نصوص؟`
- Replies: Reply to any message with `@askaosus` to use the original message as context

### Response Format

The bot provides:

- A concise answer in Arabic
- References to relevant Discourse posts
- Direct links for further reading
- Encouragement to participate in the forum community

## Configuration

The bot is configured through environment variables that can be set in your shell or directly in the Docker Compose files. All configuration options have sensible defaults where possible.

### Matrix Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MATRIX_HOMESERVER_URL` | The Matrix homeserver URL | `https://matrix.org` | ✅ |
| `MATRIX_USER_ID` | The bot's Matrix user ID (e.g., `@askaosus:matrix.org`) | `@askaosus:matrix.org` | ✅ |
| `MATRIX_PASSWORD` | The bot's Matrix account password | - | ✅ |
| `MATRIX_DEVICE_NAME` | Device name for the Matrix session | `askaosus-python` | ❌ |
| `MATRIX_STORE_PATH` | Path to store Matrix session data | `/app/data/matrix_store` | ❌ |

### Discourse Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DISCOURSE_BASE_URL` | The Discourse forum base URL | `https://discourse.aosus.org` | ❌ |
| `DISCOURSE_API_KEY` | Discourse API key for authenticated requests | - | ❌ |
| `DISCOURSE_USERNAME` | Discourse username for API authentication | - | ❌ |

> **Note**: API key and username are optional but recommended for higher rate limits and access to private content.

### LLM Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `LLM_PROVIDER` | LLM provider (`openai`, `openrouter`, `gemini`) | `openai` | ❌ |
| `LLM_API_KEY` | API key for the LLM provider | - | ✅ |
| `LLM_BASE_URL` | Custom API endpoint URL | Auto-detected based on provider | ❌ |
| `LLM_MODEL` | Model name to use | `gpt-4` | ❌ |
| `LLM_MAX_TOKENS` | Maximum tokens in response | `500` | ❌ |
| `LLM_TEMPERATURE` | Response creativity (0.0-1.0) | `0.7` | ❌ |

#### Supported LLM Providers

##### OpenAI

- Set `LLM_PROVIDER=openai`
- Uses `https://api.openai.com/v1` as base URL
- Models: `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`, etc.

##### OpenRouter

- Set `LLM_PROVIDER=openrouter`
- Uses `https://openrouter.ai/api/v1` as base URL
- Models: Any model available on OpenRouter (e.g., `openai/gpt-4`, `anthropic/claude-3-sonnet`)
- Automatically includes required headers

##### Gemini

- Set `LLM_PROVIDER=gemini`
- Uses `https://generativelanguage.googleapis.com/v1beta` as base URL
- Models: `gemini-pro`, `gemini-pro-vision`, etc.

### Bot Behavior Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BOT_RATE_LIMIT_SECONDS` | Minimum seconds between responses | `1.0` | ❌ |
| `BOT_MAX_SEARCH_RESULTS` | Maximum Discourse posts to search | `5` | ❌ |
| `BOT_DEBUG` | Enable debug mode | `false` | ❌ |

### Logging Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` | ❌ |

## Usage Examples

### Basic OpenAI Setup

```bash
export MATRIX_HOMESERVER_URL="https://matrix.org"
export MATRIX_USER_ID="@mybot:matrix.org"
export MATRIX_PASSWORD="your_matrix_password"
export LLM_PROVIDER="openai"
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4"

docker compose up -d
```

### OpenRouter Setup

```bash
export MATRIX_HOMESERVER_URL="https://matrix.aosus.org"
export MATRIX_USER_ID="@askaosus:aosus.org"
export MATRIX_PASSWORD="your_password"
export LLM_PROVIDER="openrouter"
export LLM_API_KEY="sk-or-v1-..."
export LLM_MODEL="openai/gpt-4-turbo"

docker compose up -d
```

### Development Mode

```bash
export MATRIX_PASSWORD="your_password"
export LLM_API_KEY="your_api_key"

# Use development compose with hot reload
docker compose -f docker-compose.dev.yml up --watch
```

## Troubleshooting

### Common Issues

#### Bot doesn't respond to mentions

- Check that the bot is properly logged into Matrix: `docker compose logs`
- Verify the Matrix credentials are correct
- Ensure the bot has permission to read messages in the room

#### Search returns no results

- Verify `DISCOURSE_BASE_URL` is correct
- Check if Discourse API credentials are valid (optional but recommended)
- Test the Discourse search manually: `https://discourse.aosus.org/search.json?q=your_query`

#### LLM errors

- Verify the API key is valid and has sufficient credits
- Check the model name is correct for your provider
- Ensure the base URL is appropriate for your provider

#### Rate limiting issues

- Increase `BOT_RATE_LIMIT_SECONDS` if responses are too frequent
- Check your LLM provider's rate limits
- Monitor logs for rate limit errors

### Viewing Logs

```bash
# View current logs
docker compose logs -f

# View development logs
docker compose -f docker-compose.dev.yml logs -f

# Check specific container logs
docker logs askaosus-matrix-bot
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
export BOT_DEBUG=true
export LOG_LEVEL=DEBUG
```

Or use the development compose file which has debug enabled by default.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test using the development environment
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
