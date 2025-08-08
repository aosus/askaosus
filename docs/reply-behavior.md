# Reply Behavior Configuration

This document describes the new `BOT_REPLY_BEHAVIOR` configuration option that controls how the Askaosus Matrix Bot responds to replies.

## Overview

The bot now supports three distinct reply behavior modes that determine when and how it responds to messages that are replies to other messages. This provides fine-grained control over bot interactions in Matrix rooms.

## Configuration

Set the `BOT_REPLY_BEHAVIOR` environment variable to one of the following values:

- `ignore` - Ignore all replies to messages mentioning the bot
- `mention` - Only respond to replies that also mention the bot (default)
- `watch` - Watch all replies to bot messages regardless of mentions

### Thread Depth Configuration

Set the `BOT_THREAD_DEPTH_LIMIT` environment variable to control how many messages the bot collects from reply threads in `watch` mode:

- Default: `6` messages
- Range: `1` to `20` messages (to prevent excessive API calls)
- Only applies in `watch` mode

### Example Configuration

```bash
# In your .env file or environment
BOT_REPLY_BEHAVIOR=watch
BOT_THREAD_DEPTH_LIMIT=10  # Collect up to 10 messages in thread history
```

## Behavior Modes

### `ignore` Mode

When set to `ignore`, the bot will completely ignore any message that is a reply to a message mentioning the bot, even if the reply itself mentions the bot.

**Use case:** Minimize bot chatter in busy rooms where users frequently reply to bot responses.

**Example:**
```
User1: @askaosus how do I install Ubuntu?
Bot: Here's how to install Ubuntu... [detailed response]
User2: @askaosus thanks! -> Bot ignores this (even with mention)
```

### `mention` Mode (Default)

When set to `mention`, the bot will only respond to replies if the reply itself also mentions the bot.

**Use case:** Balanced approach that reduces noise while still allowing direct follow-up questions.

**Example:**
```
User1: @askaosus how do I install Ubuntu?
Bot: Here's how to install Ubuntu... [detailed response]
User2: thanks! -> Bot ignores (no mention)
User2: @askaosus can you explain step 3? -> Bot responds (has mention)
```

### `watch` Mode

When set to `watch`, the bot will respond to all replies to its own messages, regardless of whether the reply mentions the bot. In this mode, the bot also provides **full thread context** by collecting up to `BOT_THREAD_DEPTH_LIMIT` messages from the reply chain.

**Use case:** Interactive help sessions where natural conversation flow is desired with complete context understanding.

**Thread Context Features:**
- Automatically traverses reply threads up to the configured depth limit
- Collects messages in chronological order (oldest first)  
- Identifies which messages are from the bot vs users
- Provides complete conversation history to the LLM

**Example:**
```
User1: @askaosus how do I install Ubuntu?
Bot: Here's how to install Ubuntu step by step...
User1: what about step 3? -> Bot responds with full thread context
User2: thanks! -> Bot responds with full thread context  
User1: can you explain the partitioning part? -> Bot responds with thread context
```

**Thread Context Format:**
```
Message 1 (User): how do I install Ubuntu?

Message 2 (Bot): Here's how to install Ubuntu step by step...

Message 3 (User): what about step 3?

Current reply: can you explain the partitioning part?
```

## Reply Context Handling

### Single Message Context (`ignore` and `mention` modes)

When the bot processes a reply in `ignore` or `mention` modes, it includes the context of the immediate parent message:

```
Original message: How do I install Ubuntu?

Reply: what about step 3?
```

### Thread Context (`watch` mode)

When the bot processes a reply in `watch` mode, it automatically collects the **complete thread history** up to the configured depth limit:

```
Message 1 (User): How do I install Ubuntu?

Message 2 (Bot): Here's how to install Ubuntu step by step...

Message 3 (User): what about step 3?

Message 4 (Bot): Step 3 involves partitioning...

Current reply: can you explain the partitioning part?
```

#### Thread Traversal

The bot follows the Matrix reply chain (`m.relates_to.m.in_reply_to.event_id`) backwards through the conversation:

1. Starts from the current reply message
2. Follows reply relationships up the thread
3. Collects up to `BOT_THREAD_DEPTH_LIMIT` messages  
4. Returns messages in chronological order (oldest first)
5. Identifies bot vs user messages for proper context labeling

#### Benefits of Thread Context

- **Complete Conversation Understanding**: LLM sees the full discussion history
- **Better Continuity**: References to previous messages are understood
- **Improved Relevance**: Answers can build upon the entire conversation
- **Natural Flow**: Users can refer to earlier messages without re-explaining

### Content Cleaning

The bot automatically cleans reply content by:

1. Removing bot mentions (`@askaosus`, `askaosus`)
2. Removing Matrix quote formatting (lines starting with `> `)
3. Normalizing whitespace

**Example:**
```
Input:  "> Original: How do I install Ubuntu?\n@askaosus what about this?"
Output: "what about this?"
```

### Message Tracking

The bot tracks its own message IDs to identify which messages are replies to bot responses versus replies to user messages. This enables the different behavior modes to work correctly.

## Reply Message Format

When responding to a reply, the bot sends its response as a proper Matrix reply, maintaining the conversation thread structure.

## Implementation Details

### Message Processing Logic

1. **Direct mentions**: Always processed regardless of reply behavior setting
2. **Replies to bot messages**: Processed according to `BOT_REPLY_BEHAVIOR` setting
3. **Replies to user messages**: Only processed if they mention the bot (preserves original behavior)

### Reply Detection

The bot uses Matrix's native reply structure (`m.relates_to` with `m.in_reply_to`) rather than fallback markdown formatting, ensuring reliable reply detection across all Matrix clients.

### Bot Message Identification

The bot maintains a set of message IDs for messages it has sent, allowing it to distinguish between replies to its own messages versus replies to other users' messages.

## Migration Guide

### Existing Behavior

Prior to this feature, the bot would respond to any reply that mentioned it, regardless of what message was being replied to.

### New Default Behavior

The default behavior (`mention`) maintains backward compatibility - the bot still requires mentions to respond to replies.

### Upgrading

No configuration changes are required. The bot defaults to `mention` mode, which preserves the existing behavior while providing better context handling.

## Performance Considerations

### Thread Context Collection

In `watch` mode, the bot makes additional Matrix API calls to collect thread history:

- **API Calls**: Up to `BOT_THREAD_DEPTH_LIMIT` calls to `room_get_event` 
- **Rate Limiting**: Respects Matrix rate limits automatically
- **Fallback**: If thread collection fails, falls back to single message context
- **Caching**: Matrix client handles response caching

### Configuration Recommendations

**For low-traffic rooms or detailed conversations:**
```bash
BOT_REPLY_BEHAVIOR=watch
BOT_THREAD_DEPTH_LIMIT=10
```

**For high-traffic rooms or simple interactions:**
```bash
BOT_REPLY_BEHAVIOR=mention
BOT_THREAD_DEPTH_LIMIT=3  # Not used in mention mode, but good default
```

**For minimal bot interaction:**
```bash
BOT_REPLY_BEHAVIOR=ignore
```

## Troubleshooting

## Troubleshooting

### Bot Not Responding to Replies

1. Check the `BOT_REPLY_BEHAVIOR` setting
2. Ensure replies are properly formatted by the Matrix client
3. Verify the original message was from the bot (for `watch` and `mention` modes)
4. Check bot logs for thread collection errors

### Bot Responding Too Frequently

- Consider switching from `watch` to `mention` or `ignore` mode
- Reduce `BOT_THREAD_DEPTH_LIMIT` to minimize API calls
- Check if multiple bot mentions exist in the configuration

### Context Not Included or Incomplete

**Single message context issues:**
- Check Matrix client reply formatting
- Verify the original message is accessible to the bot

**Thread context issues (watch mode):**
- Check `BOT_THREAD_DEPTH_LIMIT` configuration
- Review bot logs for Matrix API errors during thread collection
- Verify the bot has access to read message history in the room
- Check if thread depth limit is being reached (increase if needed)

### Performance Issues

**High API usage in watch mode:**
- Reduce `BOT_THREAD_DEPTH_LIMIT` to 3-6 messages
- Consider switching to `mention` mode for high-traffic rooms
- Monitor Matrix API rate limiting in bot logs

**Thread collection timeouts:**
- Check Matrix homeserver performance
- Review network connectivity to Matrix server
- Verify room message history is accessible

## Examples

### Configuration Examples

**Minimal bot interaction:**
```bash
BOT_REPLY_BEHAVIOR=ignore
# BOT_THREAD_DEPTH_LIMIT not used in ignore mode
```

**Balanced interaction (default):**
```bash
BOT_REPLY_BEHAVIOR=mention
# BOT_THREAD_DEPTH_LIMIT not used in mention mode (single message context)
```

**Maximum helpfulness with thread context:**
```bash
BOT_REPLY_BEHAVIOR=watch
BOT_THREAD_DEPTH_LIMIT=6  # Collect up to 6 messages in thread
```

**High-traffic room optimization:**
```bash
BOT_REPLY_BEHAVIOR=watch  
BOT_THREAD_DEPTH_LIMIT=3  # Reduce API calls, still provide thread context
```

### Conversation Examples

See the behavior mode sections above for detailed conversation examples showing how each mode affects bot responses.