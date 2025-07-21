# LLM Logging Feature

The Askaosus Matrix Bot now includes enhanced logging capabilities specifically designed to provide visibility into Large Language Model (LLM) operations and responses.

## Overview

This feature addresses the need to see LLM outputs in logs, which were previously not visible. The bot now includes:

- **Custom LLM log level**: A new log level specifically for LLM-related operations
- **Comprehensive LLM response logging**: Logs actual LLM responses, decisions, and processing steps  
- **Matrix-nio log filtering**: Option to exclude matrix-nio library logs for cleaner output
- **Configurable logging levels**: Fine-grained control over what gets logged

## Custom Log Level

### LLM Log Level (25)
A new custom log level `LLM` has been added at level 25, positioned between `INFO` (20) and `WARNING` (30). This level is specifically designed for LLM-related operations.

```python
logger.llm("LLM-specific message")  # Uses level 25
```

## Configuration

### Environment Variables

```bash
# Base log level (DEBUG, INFO, LLM, WARNING, ERROR)
LOG_LEVEL=INFO

# LLM-specific log level - controls LLM logger minimum level
LLM_LOG_LEVEL=LLM

# Whether to filter out matrix-nio library logs (true/false)
EXCLUDE_MATRIX_NIO_LOGS=false
```

### Log Levels Hierarchy
```
DEBUG (10) - Most verbose, includes all debug information
INFO (20)  - General information about bot operations
LLM (25)   - LLM-specific operations and responses
WARNING (30) - Warning messages
ERROR (40) - Error conditions
```

## What Gets Logged

### LLM Processing Information
- Question being processed
- System prompt length
- Number of LLM attempts and iterations
- Messages sent to LLM (count and model info)

### LLM Response Details  
- Response finish reason (e.g., 'tool_calls', 'stop')
- Response content (actual LLM text output)
- Number and types of tool calls requested
- Tool call execution details

### Search Operations
- Discourse search queries and results count
- Search context length and formatting
- URLs selected by LLM for responses

### Token Usage
- Prompt tokens, completion tokens, and total token usage
- Logged after each LLM interaction

### Processing Results
- Final responses prepared for users
- Success/failure status of question processing

## Example Log Output

```
2024-01-01 12:00:00,000 - src.llm - LLM - Processing question with tools: How do I install Ubuntu?
2024-01-01 12:00:00,001 - src.llm - LLM - System prompt length: 3099 characters
2024-01-01 12:00:00,002 - src.llm - LLM - LLM attempt 1/3
2024-01-01 12:00:00,003 - src.llm - LLM - Sending 2 messages to LLM (model: gpt-4)
2024-01-01 12:00:01,000 - src.llm - LLM - LLM response received - finish_reason: tool_calls
2024-01-01 12:00:01,001 - src.llm - LLM - LLM requested 1 tool call(s)
2024-01-01 12:00:01,002 - src.llm - LLM - Tool call 1: search_discourse
2024-01-01 12:00:01,003 - src.llm - LLM - Executing function: search_discourse
2024-01-01 12:00:01,004 - src.llm - LLM - Searching Discourse with query: 'ubuntu installation'
2024-01-01 12:00:01,100 - src.llm - LLM - Discourse search returned 3 results
2024-01-01 12:00:01,101 - src.llm - LLM - LLM selected URL to send: https://discourse.aosus.org/t/install-ubuntu/123
2024-01-01 12:00:01,102 - src.llm - LLM - Final response prepared: Here's a guide for Ubuntu installation...
2024-01-01 12:00:01,103 - src.llm - LLM - Token usage - prompt: 150, completion: 25, total: 175
2024-01-01 12:00:01,104 - src.llm - LLM - Question processing completed successfully
```

## Matrix-nio Log Filtering

When `EXCLUDE_MATRIX_NIO_LOGS=true`, the following logger families are filtered out:

- `nio.*` - Matrix-nio library logs
- `aiohttp.*` - HTTP client logs  
- `urllib3.*` - URL library logs

This provides cleaner logs focused on bot logic and LLM operations.

## Usage Recommendations

### Development and Debugging
```bash
LOG_LEVEL=LLM          # Show LLM operations and above
LLM_LOG_LEVEL=DEBUG    # Show detailed LLM debugging
EXCLUDE_MATRIX_NIO_LOGS=true  # Focus on bot logic
```

### Production Monitoring
```bash
LOG_LEVEL=INFO         # Standard information level
LLM_LOG_LEVEL=LLM      # Show LLM operations 
EXCLUDE_MATRIX_NIO_LOGS=false  # Keep all logs for debugging
```

### LLM-Only Logging
```bash
LOG_LEVEL=LLM          # Only LLM and higher levels
LLM_LOG_LEVEL=LLM      # LLM operations
EXCLUDE_MATRIX_NIO_LOGS=true   # Clean output
```

## Implementation Details

The logging functionality is implemented in:

- **`src/logging_utils.py`** - Custom log level and filtering utilities
- **`src/llm.py`** - Enhanced LLM response logging
- **`src/main.py`** - Logging configuration setup
- **`src/config.py`** - Environment variable handling

## Benefits

1. **Visibility**: See exactly what the LLM is responding with
2. **Debugging**: Track LLM decision-making process step by step
3. **Monitoring**: Monitor token usage and performance metrics
4. **Focused Logging**: Filter out noise from matrix-nio operations
5. **Configurable**: Adjust logging verbosity based on needs

This enhancement addresses issue #16 by providing comprehensive visibility into LLM operations while maintaining the ability to filter out unrelated library logs.