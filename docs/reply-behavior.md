# Reply Behavior Configuration

This document describes the new `BOT_REPLY_BEHAVIOR` configuration option that controls how the Askaosus Matrix Bot responds to replies.

## Overview

The bot now supports three distinct reply behavior modes that determine when and how it responds to messages that are replies to other messages. This provides fine-grained control over bot interactions in Matrix rooms.

## Configuration

Set the `BOT_REPLY_BEHAVIOR` environment variable to one of the following values:

- `ignore` - Ignore all replies to messages mentioning the bot
- `mention` - Only respond to replies that also mention the bot (default)
- `watch` - Watch all replies to bot messages regardless of mentions

### Example Configuration

```bash
# In your .env file or environment
BOT_REPLY_BEHAVIOR=watch
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

When set to `watch`, the bot will respond to all replies to its own messages, regardless of whether the reply mentions the bot.

**Use case:** Interactive help sessions where natural conversation flow is desired.

**Example:**
```
User1: @askaosus how do I install Ubuntu?
Bot: Here's how to install Ubuntu... [detailed response]
User2: what about step 3? -> Bot responds (reply to bot message)
User2: thanks! -> Bot responds (reply to bot message)
```

## Reply Context Handling

### Thread Context

When the bot processes a reply, it automatically includes the context of the original message to provide better assistance:

```
Original message: How do I install Ubuntu?

Reply: what about step 3?
```

The bot receives both messages as context, enabling more coherent responses.

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

## Troubleshooting

### Bot Not Responding to Replies

1. Check the `BOT_REPLY_BEHAVIOR` setting
2. Ensure replies are properly formatted by the Matrix client
3. Verify the original message was from the bot (for `watch` and `mention` modes)

### Bot Responding Too Frequently

- Consider switching from `watch` to `mention` or `ignore` mode
- Check if multiple bot mentions exist in the configuration

### Context Not Included

The bot automatically includes context for all replies. If context is missing:
- Check Matrix client reply formatting
- Verify the original message is accessible to the bot

## Examples

### Configuration Examples

**Minimal bot interaction:**
```bash
BOT_REPLY_BEHAVIOR=ignore
```

**Balanced interaction (default):**
```bash
BOT_REPLY_BEHAVIOR=mention
```

**Maximum helpfulness:**
```bash
BOT_REPLY_BEHAVIOR=watch
```

### Conversation Examples

See the behavior mode sections above for detailed conversation examples showing how each mode affects bot responses.