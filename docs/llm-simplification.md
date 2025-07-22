# LLM System Simplification

## Overview

The LLM system has been simplified to use only the `search_discourse` tool, with the LLM providing direct responses instead of using dedicated response tools.

## Changes Made

### 1. Tool Deprecation

**Removed Tools:**
- `send_link`: Previously used to send URLs to users
- `no_result_message`: Previously used to send "no results" messages

**Remaining Tool:**
- `search_discourse`: Search the Discourse forum (unchanged functionality)

### 2. Response Handling

**Before:** LLM called `send_link` or `no_result_message` tools to respond
**After:** LLM provides direct text responses that may include URLs

**UTM Tags:** Automatically applied to any URLs in LLM responses

### 3. Error Messages

**New Error Messages:**
- `rate_limit_error`: When Discourse API returns 429 (rate limit)
- `discourse_unreachable`: When Discourse API is unreachable or returns errors
- `llm_down`: When LLM service encounters errors

**Removed Error Messages:**
- `no_results_found`
- `processing_error` 
- `search_error`
- `fallback_error`

### 4. Exception Handling

**New Exception Classes:**
- `DiscourseRateLimitError`: Raised on HTTP 429 responses
- `DiscourseConnectionError`: Raised on connection or HTTP errors

**Error Flow:**
1. Discourse search attempts detect rate limits (429) and connection errors
2. Appropriate exceptions are raised and caught in LLM client
3. Specific error messages are returned to users

### 5. System Prompt Updates

- Removed references to `send_link` and `no_result_message` tools
- Updated guidelines to focus on direct responses with embedded URLs
- Simplified response examples

## Preserved Features

- **Search Functionality:** Unchanged `search_discourse` tool with adjustable limits
- **Context Handling:** Reply context processing remains intact
- **UTM Tracking:** URLs in LLM responses automatically get UTM parameters
- **Iterative Search:** LLM can still perform multiple searches per question
- **Logging:** Enhanced LLM logging remains functional

## Code Changes

### Files Modified:
- `src/llm.py`: Simplified tool calling, added error handling
- `src/discourse.py`: Added exception classes and error detection
- `src/responses.py`: Updated error message configuration  
- `src/bot.py`: Updated error handling for LLM failures
- `responses.json`: New error message templates
- `system_prompt.md`: Simplified tool descriptions

### Files Unchanged:
- `src/config.py`: UTM and other configuration preserved
- `src/main.py`: Entry point unchanged
- Core Matrix functionality preserved

## Benefits

1. **Simplified Architecture:** Fewer tools means less complexity
2. **Better Error Handling:** Specific error messages for different failure modes
3. **Direct Responses:** LLM can provide more natural, contextual responses
4. **Preserved Features:** All existing functionality maintained
5. **Better Debugging:** Clear error paths for different failure scenarios

## Testing

Run the test suite to verify all changes:

```bash
python3 test_simplified_system.py
```

Expected output: All tests should pass, confirming:
- Tool simplification
- Error message updates
- Exception handling
- UTM preservation
- System prompt updates
