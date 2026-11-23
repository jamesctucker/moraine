# Headroom pack

[Headroom](https://github.com/headroomlabs-ai/headroom) MCP server: context compression for tool output (60–95% fewer tokens, reversible via CCR).

## How it works

Content-type-aware compressors (JSON, code, logs, diffs, search results, text) feed into a Compress-Cache-Retrieve (CCR) store so compression stays reversible — the agent can ask for the original whenever it wants.

## Setup

```bash
uv tool install "headroom-ai[mcp]"   # or: pipx install "headroom-ai[mcp]"
```

The MCP server (`headroom mcp serve`) is registered by `moraine sync` while this pack is enabled. `bash scripts/setup` can also provision it.

Avoid bare `pip install` into a system Python — keep the install workspace-local or tool-isolated.

## MCP tools

- `headroom_compress(content)` — compress content on demand, returns compressed text + hash for retrieval
- `headroom_retrieve(hash, query?)` — retrieve original uncompressed content, optionally filtered by query
- `headroom_stats` — session compression statistics (tokens saved, cost saved, recent events)

## What NOT to use it for

Codebase search (use your semantic search tool) or session search (use `scripts/workspace/session-index.py`): CCR retrieves previously compressed content; it is not a search index.
