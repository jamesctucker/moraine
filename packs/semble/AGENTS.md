# Semble pack

Semble MCP server: semantic (natural-language) code search across your repos.

## Setup

Needs `uv` (see `pack.yaml` for install commands). The pinned server (`uvx --from semble[mcp]==0.7.3 semble`) is registered by `moraine sync` while this pack is enabled.

## When to use it

Prefer it over `grep` for conceptual code queries — "find authentication logic", "where is the payment flow?" Use `grep` only for exact string matching.

Semble searches the repos it has been pointed at; index a repo from inside it before expecting results.
