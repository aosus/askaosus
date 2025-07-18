# Context Handling Feature

## Overview

The Matrix Bot supports advanced context handling when users mention the bot in reply to another message. This feature enables the bot to understand the full conversation context and provide more relevant responses.

## How It Works

### Basic Mention Behavior

When a user mentions the bot directly in a message:
```
@botname How do I install software?
```

The bot receives only the mentioning message and searches the forum for relevant content.

### Reply with Context Behavior

When a user mentions the bot while replying to another message:

1. **Original Message**: "I'm having trouble with my graphics driver"
2. **Reply with Mention**: "@botname can you help with this?"

The bot now receives both messages as context:
- Original message: "I'm having trouble with my graphics driver"
- Reply: "can you help with this?"

### Context Processing

The bot combines both messages to understand the full context:
```
Original message: I'm having trouble with my graphics driver

Reply: can you help with this?
```

This allows the LLM to:
- Understand what "this" refers to in the reply
- Search for content related to graphics driver issues
- Provide more targeted and relevant responses

## Implementation Details

### Message Detection

The bot detects when a mentioning message is a reply by checking for:
- `m.relates_to.m.in_reply_to.event_id` in the message content
- A valid event ID referencing the original message

### Original Message Fetching

When a reply is detected, the bot **always** attempts to provide context:
1. Extracts the event ID of the original message
2. Uses the Matrix `room_get_event` API to fetch the original message
3. Handles different message types appropriately:
   - Text messages: Uses the full text content
   - Non-text messages: Provides a descriptive placeholder (e.g., "[Image - content not accessible as text]")
4. **Guarantees context**: Even if fetching fails, provides a fallback message "[Original message could not be retrieved]"
5. Combines both messages as context for the LLM

### Error Handling

The feature includes robust error handling with **guaranteed context provision**:
- **Always provides context** when a reply is detected, even if the original message cannot be fetched
- Non-text messages (images, files, etc.) are handled with descriptive placeholders
- Network errors and permission issues result in fallback context rather than failure
- All errors are logged for debugging but don't break the bot functionality

### Context Format

The LLM receives the context in this format:
```
Original message: [content of the replied-to message OR fallback message]

Reply: [content of the mentioning message, with mention removed]
```

Possible original message formats:
- `[Original message text]` - Successfully fetched text message
- `[Image - content not accessible as text]` - Non-text message type
- `[Original message could not be retrieved]` - Fetch failed

## Configuration

No additional configuration is required. The feature works automatically when:
- The bot is mentioned in a reply to another message
- The feature provides context regardless of message accessibility

## Benefits

1. **Better Context Understanding**: The bot can understand what users are referring to
2. **More Relevant Results**: Search queries can be more targeted based on full context
3. **Improved User Experience**: Users can ask follow-up questions naturally
4. **Conversation Continuity**: Maintains context across multiple message exchanges
5. **Robust Operation**: Always provides context, even when original messages are inaccessible

## Example Usage

### Scenario 1: Technical Support
```
User A: "My system crashes when I run the command `sudo apt update`"
User B: "@botname what could be causing this?"
```

The bot receives:
- Original: "My system crashes when I run the command `sudo apt update`"
- Reply: "what could be causing this?"

Result: Bot searches for apt update crash issues specifically.

### Scenario 2: Software Recommendation
```
User A: "I need a good video editor for Linux"
User B: "@botname any suggestions for this?"
```

The bot receives:
- Original: "I need a good video editor for Linux"
- Reply: "any suggestions for this?"

Result: Bot searches for Linux video editor recommendations.

### Scenario 3: Non-text Original Message
```
User A: [Uploads screenshot of error]
User B: "@botname what does this error mean?"
```

The bot receives:
- Original: "[Image - content not accessible as text]"
- Reply: "what does this error mean?"

Result: Bot searches for general error troubleshooting information.

## Technical Notes

- Uses Matrix nio library's `room_get_event` method
- Supports text messages with full context, provides placeholders for non-text messages
- Context is limited to the immediate reply relationship (no deep threading)
- **Guaranteed context provision**: Always provides some form of context when a reply is detected
- Graceful degradation: Falls back to descriptive placeholders when content is not accessible

## Future Enhancements

Potential improvements could include:
- Support for deeper conversation threading
- Context from multiple previous messages
- Enhanced handling of non-text message types (OCR for images, file content analysis)
- Conversation memory across sessions
