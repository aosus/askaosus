# OpenRouter Provider Configuration

This document describes the OpenRouter provider routing configuration options added to the Askaosus Matrix Bot.

## Overview

The bot now supports two new environment variables that allow you to control how OpenRouter routes your LLM requests:

1. **`LLM_OPENROUTER_SORTING`** - Control provider sorting by performance metric
2. **`LLM_OPENROUTER_PROVIDER`** - Manually select a specific provider

These options are only used when `LLM_PROVIDER=openrouter`.

## Configuration Options

### Provider Sorting (`LLM_OPENROUTER_SORTING`)

Control how OpenRouter sorts and selects providers based on performance metrics:

- `throughput` - Sort providers by throughput (requests/second)
- `latency` - Sort providers by response latency (fastest first)
- `price` - Sort providers by cost (cheapest first)

**Example:**
```bash
LLM_OPENROUTER_SORTING=latency
```

This will route requests to the fastest responding providers for your chosen model.

### Manual Provider Selection (`LLM_OPENROUTER_PROVIDER`)

Manually lock to a specific provider, bypassing automatic routing:

**Example:**
```bash
LLM_OPENROUTER_PROVIDER=anthropic
```

This will always route requests to Anthropic, regardless of other settings.

**Common providers:**
- `anthropic` - Anthropic's Claude models
- `openai` - OpenAI's GPT models
- `google` - Google's Gemini models
- `meta` - Meta's Llama models
- `mistral` - Mistral AI models

## Priority and Behavior

- **Manual provider** (`LLM_OPENROUTER_PROVIDER`) takes precedence over sorting preferences
- If both are set, only the manual provider selection is used
- If neither is set, OpenRouter uses its default load balancing
- Configuration is ignored when using other LLM providers (OpenAI, Gemini)

## Examples

### Example 1: Optimize for Speed
```bash
LLM_PROVIDER=openrouter
LLM_OPENROUTER_SORTING=latency
LLM_MODEL=anthropic/claude-3.5-sonnet
```

### Example 2: Optimize for Cost
```bash
LLM_PROVIDER=openrouter
LLM_OPENROUTER_SORTING=price
LLM_MODEL=gpt-4
```

### Example 3: Lock to Specific Provider
```bash
LLM_PROVIDER=openrouter
LLM_OPENROUTER_PROVIDER=openai
LLM_MODEL=gpt-4
```

### Example 4: High Throughput
```bash
LLM_PROVIDER=openrouter
LLM_OPENROUTER_SORTING=throughput
LLM_MODEL=meta/llama-3-8b
```

## Technical Details

When configured, the bot adds a `provider` object to OpenRouter API requests:

```json
{
  "model": "anthropic/claude-3.5-sonnet",
  "messages": [...],
  "provider": {
    "order": ["auto:latency"]
  }
}
```

For manual provider selection:
```json
{
  "provider": {
    "order": ["anthropic"]
  }
}
```

## Validation

The configuration includes validation:
- Only `throughput`, `latency`, and `price` are accepted for sorting
- Invalid sorting options will cause startup errors
- Provider names are not validated (passed directly to OpenRouter)

## Logging

When OpenRouter provider configuration is active, you'll see log entries like:

```
INFO:   OpenRouter sorting: latency
INFO:   OpenRouter provider: auto
```

Or for manual provider:
```
INFO:   OpenRouter sorting: default
INFO:   OpenRouter provider: anthropic
```

For more information about OpenRouter provider routing, see: https://openrouter.ai/docs/features/provider-routing