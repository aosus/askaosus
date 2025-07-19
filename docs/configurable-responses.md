# Configurable Responses System

The Askaosus Matrix Bot now supports configurable responses through an external JSON file instead of hardcoded messages. This allows for easy customization of bot responses without modifying the source code, making it perfect for communities that want to customize responses for their own language and culture.

## Configuration File

### Location
The bot looks for the responses configuration file in the following locations (in order):
1. `/app/responses.json` (Production Docker environment)
2. `responses.json` (Development - current directory)
3. `src/../responses.json` (Relative to source directory)

If no configuration file is found, the bot falls back to hardcoded default responses.

### Structure

The `responses.json` file contains categorized responses in a simple key-value structure:

```json
{
  "error_messages": {
    "no_results_found": "Sorry, I couldn't find any relevant topics for your question..."
  },
  "discourse_messages": {
    "untitled_post": "Untitled post"
  },
  "system_messages": {
    "perfect_match": "I found a perfect match for your question:"
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

# Get messages by category and key
message = response_config.get_error_message("no_results_found")
discourse_msg = response_config.get_discourse_message("untitled_post")
```

## Customization

To customize responses for your community:

1. **Edit existing responses**: Modify values in `responses.json` to match your community's language and tone
2. **Add new response types**: Add new keys under existing categories
3. **Add new categories**: Add new top-level categories as needed

Example of customizing for Arabic community:
```json
{
  "error_messages": {
    "no_results_found": "عذراً، لم أتمكن من العثور على موضوعات ذات صلة بسؤالك. يرجى المحاولة بصيغة مختلفة أو زيارة المنتدى مباشرة."
  },
  "discourse_messages": {
    "untitled_post": "منشور بدون عنوان"
  }
}
```

Example of customizing for French community:
```json
{
  "error_messages": {
    "no_results_found": "Désolé, je n'ai trouvé aucun sujet pertinent à votre question. Veuillez reformuler votre demande ou visiter directement le forum."
  },
  "discourse_messages": {
    "untitled_post": "Article sans titre"
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
- Missing file graceful handling  
- Custom configuration support
- Integration completeness