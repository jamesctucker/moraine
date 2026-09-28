# Readwise Setup (Shared)

All Readwise skills in this workspace use the same MCP server or CLI fallback.

## Access

Check if Readwise MCP tools are available (e.g. `mcp__readwise__reader_list_documents`). If they are, use them throughout. If not, use the equivalent `readwise` CLI commands instead (e.g. `readwise list`, `readwise read <id>`, `readwise move <id> <location>`). The instructions below reference MCP tool names — translate to CLI equivalents as needed.

## Full Tool Reference

See [REFERENCE.md](REFERENCE.md) for complete tool signatures, parameters, and example workflows.

## Persona File

Most Readwise skills check for `reader_persona.md` in the current directory. If it exists, use it to personalize output. If not, proceed without it — note briefly that the experience will be less personalized, and suggest running `build-persona` first.
