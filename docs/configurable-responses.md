# Configurable Responses System

The Askaosus Matrix Bot now supports configurable responses through an external JSON file instead of hardcoded messages. This allows for easy customization of bot responses without modifying the source code.

## Configuration File

### Location
The bot looks for the responses configuration file in the following locations (in order):
1. `/app/responses.json` (Production Docker environment)
2. `responses.json` (Development - current directory)
3. `src/../responses.json` (Relative to source directory)

If no configuration file is found, the bot falls back to hardcoded default responses.

### Structure

The `responses.json` file contains categorized responses with multi-language support:

```json
{
  "error_messages": {
    "no_results_found": {
      "ar": "Arabic message",
      "en": "English message"
    }
  },
  "discourse_messages": {
    "untitled_post": {
      "ar": "منشور بدون عنوان",
      "en": "Untitled post"
    }
  }
}
```

### Categories

#### error_messages
- **no_results_found**: When no search results are found
- **processing_error**: General LLM processing errors  
- **search_error**: Search operation failures
- **fallback_error**: Final fallback error message

#### discourse_messages  
- **no_results**: When Discourse search returns empty
- **untitled_post**: Default title for posts without titles
- **untitled_topic**: Default title for topics without titles
- **default_excerpt**: Default excerpt for topics without content

#### system_messages
- **perfect_match**: When an exact match is found
- **closest_match**: When showing the best available result

## Usage

### ResponseConfig Class

```python
from responses import ResponseConfig

# Initialize with default path detection
response_config = ResponseConfig()

# Or specify custom path
response_config = ResponseConfig("/path/to/custom/responses.json")

# Get messages by category, key, and language
message = response_config.get_error_message("no_results_found", "en")
discourse_msg = response_config.get_discourse_message("untitled_post", "ar")
```

### Language Fallback

The system provides intelligent language fallback:
1. Returns requested language if available
2. Falls back to Arabic (ar) if requested language missing
3. Falls back to English (en) if Arabic missing
4. Returns generic error message if neither available

## Customization

To customize responses:

1. **Edit existing responses**: Modify values in `responses.json`
2. **Add new languages**: Add language codes to existing messages
3. **Add new response types**: Add new keys under existing categories
4. **Add new categories**: Add new top-level categories with appropriate structure

Example of adding French support:
```json
{
  "error_messages": {
    "no_results_found": {
      "ar": "عذراً، لم أتمكن من العثور على موضوعات ذات صلة",
      "en": "Sorry, I couldn't find any relevant topics",
      "fr": "Désolé, je n'ai trouvé aucun sujet pertinent"
    }
  }
}
```

## Backward Compatibility

The system maintains full backward compatibility:
- If `responses.json` is missing, hardcoded responses are used
- If a specific response is missing, fallback responses are provided
- Existing bot behavior is unchanged when configuration file is present

## Testing

Test the configuration system:
```bash
python test_responses.py
```

This tests:
- Configuration file loading
- Language fallback behavior
- Missing file graceful handling  
- Custom configuration support
- Integration completeness