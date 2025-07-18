# UTM Tracking Feature

## Overview

The Matrix Bot supports automatic UTM parameter injection for all forum links shared with users. This feature enables tracking of how users discover content through the bot's recommendations.

## Configuration

UTM tracking is configured using the `BOT_UTM_TAGS` environment variable. The format follows standard URL query parameter syntax.

### Environment Variable Format

```bash
BOT_UTM_TAGS="utm_source=value&utm_medium=value&utm_campaign=value&utm_content=value&utm_term=value"
```

### Example Configuration

```bash
export BOT_UTM_TAGS="utm_source=matrixbot&utm_medium=matrix&utm_campaign=support&utm_content=auto_response"
```

## How It Works

1. **Link Detection**: When the LLM calls the `send_link` function with a forum URL
2. **UTM Injection**: The bot automatically appends the configured UTM parameters to the URL
3. **Graceful Fallback**: If UTM tag processing fails, the original URL is used without modification
4. **Preservation**: Existing query parameters in the original URL are preserved

## Implementation Details

### URL Processing

The bot uses Python's `urllib.parse` module to safely add UTM parameters:

1. Parses the original URL
2. Extracts existing query parameters
3. Adds configured UTM parameters
4. Reconstructs the URL with both original and UTM parameters

### Error Handling

- Invalid UTM tag format: Falls back to original URL
- URL parsing errors: Falls back to original URL
- All errors are logged for debugging but don't break bot functionality

### Example Transformation

**Original URL:**
```
https://discourse.aosus.org/t/how-to-install-software/123
```

**With UTM tags:**
```
https://discourse.aosus.org/t/how-to-install-software/123?utm_source=matrixbot&utm_medium=matrix&utm_campaign=support
```

**URL with existing parameters:**
```
Original: https://discourse.aosus.org/search?q=software
Result: https://discourse.aosus.org/search?q=software&utm_source=matrixbot&utm_medium=matrix&utm_campaign=support
```

## Analytics Integration

UTM parameters can be tracked using:

- **Google Analytics**: Automatic UTM parameter recognition
- **Discourse Analytics**: Custom tracking setup may be required
- **Server Logs**: UTM parameters appear in access logs
- **Third-party Analytics**: Most platforms support UTM parameter tracking

## Common UTM Parameters

| Parameter | Purpose | Example Values |
|-----------|---------|----------------|
| `utm_source` | Traffic source | `matrixbot`, `chatbot`, `askaosus_bot` |
| `utm_medium` | Marketing medium | `matrix`, `chat`, `instant_message` |
| `utm_campaign` | Campaign name | `support`, `help`, `user_assistance` |
| `utm_content` | Content differentiation | `auto_response`, `search_result` |
| `utm_term` | Paid search keywords | Usually not applicable for bots |

## Best Practices

### Naming Conventions

- Use consistent, descriptive values
- Avoid special characters and spaces
- Use underscores or hyphens for readability
- Keep values short but meaningful

### Recommended Configuration

For a Matrix support bot:
```bash
BOT_UTM_TAGS="utm_source=matrix_bot&utm_medium=matrix&utm_campaign=user_support"
```

For tracking specific bot instances:
```bash
BOT_UTM_TAGS="utm_source=askaosus_bot&utm_medium=matrix&utm_campaign=community_support&utm_content=automated"
```

## Privacy Considerations

- UTM parameters are visible in URLs
- Consider user privacy when defining parameter values
- Avoid including personally identifiable information
- Follow your organization's privacy policies

## Troubleshooting

### UTM Tags Not Appearing

1. Verify `BOT_UTM_TAGS` environment variable is set
2. Check the format follows `key=value&key=value` syntax
3. Review logs for UTM processing errors
4. Ensure the bot restart after configuration changes

### Invalid URL Format

- Check for special characters in UTM values
- Ensure proper URL encoding if needed
- Verify no syntax errors in the environment variable

### Analytics Not Tracking

- Verify analytics platform supports UTM parameters
- Check UTM parameter names match platform expectations
- Ensure analytics tracking code is properly installed on the target site

## Configuration Examples

### Google Analytics Tracking

```bash
BOT_UTM_TAGS="utm_source=matrix_bot&utm_medium=chat&utm_campaign=forum_support&utm_content=ai_response"
```

### Simple Source Tracking

```bash
BOT_UTM_TAGS="utm_source=chatbot&utm_medium=matrix"
```

### Campaign-Specific Tracking

```bash
BOT_UTM_TAGS="utm_source=askaosus&utm_medium=matrix&utm_campaign=q1_2024_support"
```

## Logging

UTM tag processing is logged at the INFO level:
- Configuration presence is logged at startup
- Processing errors are logged as warnings
- Original URLs are preserved in error cases

To monitor UTM tag functionality:
```bash
# Check if UTM tags are configured
grep "UTM tags configured" logs/bot.log

# Monitor UTM processing errors
grep "Failed to add UTM tags" logs/bot.log
```
