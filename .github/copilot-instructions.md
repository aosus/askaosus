# GitHub Copilot Instructions for Askaosus Matrix Bot

This guide helps AI coding agents quickly navigate, understand, and extend the Askaosus Matrix Bot project.

## 1. Big-Picture Architecture

- **Entry Point**: `src/main.py`
  - Loads environment via `load_dotenv(override=False)`
  - Configures logging and signal handlers
  - Calls `AskaosusBot.start()`
- **Configuration**: `src/config.py`
  - Reads required and optional env vars for Matrix, Discourse, LLM
  - Validates URLs, sets default base URLs
- **Bot Core**: `src/bot.py`
  - Wraps `nio.AsyncClient` for Matrix interactions
  - Manages session restore/login with `session.json` in `MATRIX_STORE_PATH`
  - Registers event callbacks: `message_callback` and `sync_callback`
  - Orchestrates searches (Discourse) and LLM calls
  - **Enhanced Context Handling**: Automatically fetches replied-to messages when bot is mentioned in a reply
    - Uses `room_get_event` to fetch original message content
    - **Guarantees context provision**: Always provides context when a reply is detected, even if original message fetch fails
    - Handles different message types gracefully (text, images, files, etc.)
    - Combines both original and reply messages as context for LLM
    - Provides fallback context for error scenarios
    - Graceful fallback if original message cannot be fetched
- **Discourse Search**: `src/discourse.py`
  - `DiscourseSearcher.search(query)`: builds variants (original, keywords, English, terms)
  - Applies `in:first` filter across variants before full-text fallback
  - Parses JSON into `DiscoursePost` dataclass
- **LLM Integration**: `src/llm.py`
  - `LLMClient` wraps `AsyncOpenAI` with tool-calling capabilities
  - Uses OpenRouter-compatible API for LLM access
  - Implements iterative search with `BOT_MAX_SEARCH_ITERATIONS`
  - Loads `system_prompt.md` for system instructions
  - Supports tool-calling functions: `search_discourse`, `send_link`, `no_result_message`

## 2. Developer Workflows

- **Production**:
  ```bash
  docker compose up -d
  ```
- **Development** (no Docker):
  ```bash
  pip install -r requirements.txt    # includes dev deps (watchgod)
  python dev.py                     # auto-reload on src/ changes
  ```
- **Debug Search**:
  Set `BOT_DEBUG=true` to run `test_discourse_search()` on startup (in `main.py`).
- **Logs**:
  - Stdout and `/app/logs/bot.log`
  - Use `LOG_LEVEL=DEBUG` for detailed logs

## 3. Project-Specific Patterns

- **Async-first**: All I/O uses `asyncio`, `aiohttp`, and `nio.AsyncClient`.
- **Session Persistence**: Stored to `session.json` in `MATRIX_STORE_PATH` to skip repeated login.
- **Search Strategy**: Uses LLM tool-calling with iterative search refinement
- **Enhanced Context Awareness**: When mentioned in replies, **always** combines original and reply messages for better context understanding
  - **Robust implementation**: Guarantees context provision even when original message is inaccessible
  - **Graceful degradation**: Handles different message types and error scenarios appropriately
  - **Universal applicability**: Works with any Matrix room and message type
- **Tool-calling Functions**:
  - `search_discourse`: Search Discourse forum with query variants
  - `send_link`: Send relevant topic URL to user
  - `no_result_message`: Handle cases when no results found
- **Logging Conventions**: INFO for flow milestones, DEBUG for deep data (LLM prompt lengths, excerpts).
- **Dataclasses**: `DiscoursePost` used to encapsulate search results.
- **Context Processing**: Replies to messages include original message content for better context understanding
- **Docker first**: project will be run in a docker container environment in production
- **documentation**: new features or big changes should be documented under the docs/ directory, with a short overview of that part and how it works.

## 4. Key Integration Points

- **Matrix (nio)**:
  - `login()`, `sync()`, `sync_forever()`, `room_send()`, `add_event_callback()`
  - Session file: `session.json` under `MATRIX_STORE_PATH`
- **Discourse (REST)**:
  - Endpoint: `GET {DISCOURSE_BASE_URL}/search.json?q=<query>`
  - Params: `order=relevance`, `limit` based on `BOT_MAX_SEARCH_RESULTS`
- **OpenAI (async)**:
  - Method: `client.chat.completions.create(model, messages, tools, tool_choice="auto")`
  - Uses OpenRouter-compatible API endpoints

## 5. Quick References

- **Env Vars**: Defined in `.env` (loaded in `main.py`)
- **Source Files**:
  - Config: `src/config.py`
  - Bot logic: `src/bot.py`
  - Search: `src/discourse.py`
  - LLM: `src/llm.py`
- **Key Config**:
  - `BOT_MAX_SEARCH_ITERATIONS`: Max search attempts per question
  - `BOT_MAX_SEARCH_RESULTS`: Max results to return
  - `LLM_MODEL`: OpenAI model to use via OpenRouter