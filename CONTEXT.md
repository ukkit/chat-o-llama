# Domain Glossary — chat-o-llama

Use these terms consistently across code, comments, and architecture discussions.

---

## Conversation

A named thread of Messages between a user and a Backend. Persisted in the `conversations` table with a model name, backend type, and timestamps. A Conversation belongs to exactly one model — switching models starts a new Conversation.

## Message

A single turn in a Conversation. Has a `role` (`user`, `assistant`, or `system`), `content`, and optional metrics (estimated tokens, response time). Stored in the `messages` table. Raw Messages come back from storage exactly as saved — no transformation applied.

## Backend

An LLM inference provider. Two concrete implementations exist: **Ollama** (remote HTTP API) and **llama.cpp** (local process). One Backend is active at a time, selected by config or explicit switch. The `LLMInterface` abstract class is the seam that all Backends satisfy.

## Backend Type

The identifier string for a Backend kind: `"ollama"` or `"llamacpp"`. Stored on Messages and Conversations so history is traceable to the Backend that produced it.

## Chat Context

The token-bounded, optionally compressed, LLM-formatted slice of a Conversation's Messages ready for submission to a Backend. Produced by `build_chat_context()`. Distinct from raw Messages: may be compressed, and is formatted as `{role, content}` dicts. Summary Messages are promoted to `system` role.

## Context Window

The maximum token budget a Backend accepts for a single inference request. Model-specific; configured via `num_ctx`. The Chat Context must fit within it.

## Compression

The process of reducing a set of Messages to fit within a Context Window while preserving meaning. Applied during Chat Context preparation when token count exceeds the configured threshold. Produces a `compression_metadata` dict alongside the reduced Message list.

## Compression Strategy

A specific algorithm for compressing Messages. Examples: `rolling_window` (discard oldest), `intelligent_summary` (summarise old turns into a system Message). The Compression Engine selects a Strategy based on conversation characteristics.

## Compression Engine

Selects and applies a Compression Strategy. Owned by `utils/compression_engine.py`. Called by `ContextCompressor`, not by routes or storage directly.

## Token Estimation

Approximating token counts for Messages without a tokenizer. Uses model-specific character-to-token ratios with language-aware adjustments. Owned by `utils/token_estimation.py`.

## Request

A single inference invocation, tracked from creation through completion or cancellation. Identified by a UUID. Supports cancellation via a `CancellationToken`. Managed by `RequestManager`.

## MCP Server

An external tool server connected via the Model Context Protocol. Provides named Tools (e.g., file operations, memory storage) that can be invoked during a chat turn. Managed by `MCPManager`.

## Tool

A named, callable capability exposed by an MCP Server. Invoked by detecting intent in the user's Message and calling the server synchronously before generating a response.
