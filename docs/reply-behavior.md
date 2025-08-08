# Reply Behavior Configuration

The Askaosus Matrix Bot supports configurable reply behavior through the `BOT_REPLY_BEHAVIOR` environment variable. This feature allows you to control how the bot responds to messages that are replies to other messages.

## Configuration

Add the following to your `.env` file:

```bash
BOT_REPLY_BEHAVIOR=mention
```

## Available Options

### `ignore` (Ignore all replies)
When set to `ignore`, the bot will completely ignore all replies, even if they mention the bot. This is useful in situations where you want the bot to only respond to direct messages and not get involved in reply chains.

**Behavior:**
- ❌ Replies with bot mentions: Ignored
- ❌ Replies without bot mentions: Ignored  
- ✅ Regular messages with bot mentions: Processed

**Example:**
```
User1: What is Python?
User2: @askaosus Can you help?  # Bot will NOT respond (it's a reply)
User2: @askaosus What about Java?  # Bot WILL respond (not a reply)
```

### `mention` (Only replies with mentions - Default)
When set to `mention`, the bot will only process replies that explicitly mention the bot. This is the default behavior and maintains backward compatibility.

**Behavior:**
- ✅ Replies with bot mentions: Processed with original message context
- ❌ Replies without bot mentions: Ignored
- ✅ Regular messages with bot mentions: Processed

**Example:**
```
User1: What is Python?
User2: @askaosus Can you elaborate on this?  # Bot responds with context
User2: I agree with this  # Bot ignores (no mention)
```

### `watch` (Watch all replies)
When set to `watch`, the bot will process all replies, regardless of whether they mention the bot. This is useful for providing comprehensive help in discussions.

**Behavior:**
- ✅ Replies with bot mentions: Processed with original message context
- ✅ Replies without bot mentions: Processed with original message context
- ✅ Regular messages with bot mentions: Processed

**Example:**
```
User1: What is Python?
User2: @askaosus Can you elaborate?  # Bot responds with context
User2: I need more details  # Bot also responds with context
```

## Context Handling

When processing replies, the bot automatically fetches the original message content and includes it as context for better understanding:

```
Original message: What is the best programming language for beginners?

Reply: I think Python is great
```

This context is sent to the LLM to provide more relevant and helpful responses.

## Error Handling

The bot gracefully handles various error scenarios:

- **Original message fetch fails**: Provides fallback context indicating the message could not be retrieved
- **Non-text original messages**: Indicates the message type (e.g., image, file) when the content cannot be accessed as text
- **Network errors**: Continues processing with fallback context

## Matrix Protocol Integration

The feature uses Matrix's native reply format (`m.relates_to` with `m.in_reply_to`) as specified in the Matrix specification, ensuring compatibility with all Matrix clients.

## Migration

If you're upgrading from a previous version:

- **No action required**: The default behavior (`mention`) maintains existing functionality
- **To disable reply processing**: Set `BOT_REPLY_BEHAVIOR=ignore`  
- **To enable comprehensive reply monitoring**: Set `BOT_REPLY_BEHAVIOR=watch`

## Validation

The configuration is validated at startup. Invalid values will cause the bot to fail with a clear error message:

```
ValueError: Invalid BOT_REPLY_BEHAVIOR. Must be one of: {'ignore', 'mention', 'watch'}
```