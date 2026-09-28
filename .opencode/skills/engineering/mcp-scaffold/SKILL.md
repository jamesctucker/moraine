---
name: mcp-scaffold
description: Scaffold a new local MCP server for OpenCode. Use when the user wants to create a new MCP server, expose an API as MCP tools, or integrate a new service into the agent's toolset.
---

# MCP Server Scaffolding

Create a new local MCP server that exposes an external API as structured tools for OpenCode agents.

## When to load this skill

- User says "create an MCP server for [service]", "scaffold MCP", "expose [API] as MCP tools"
- User wants to integrate a new service into the agent's toolset via MCP

## Architecture

Local MCP servers in this workspace use:

- **Runtime**: Node.js (ESM, `.mjs` extension)
- **SDK**: `@modelcontextprotocol/sdk` (installed in `scripts/mcp-servers/`)
- **Transport**: Stdio (agent launches the server process)
- **Config**: Registered in `.opencode/opencode.json` under `mcp.<name>`

## Scaffolding workflow

1. **Gather requirements** — Ask the user:
   - What service/API to expose?
   - What operations should be tools? (list, search, get, create, etc.)
   - Auth method: API key, env var, OAuth, none?
   - Any rate limits or pagination to handle?

2. **Create the server file** — Write to `scripts/mcp-servers/<name>-mcp.mjs` using the template below.

3. **Register in opencode.json** — Add a `local` entry:
   ```json
   "<name>": {
     "type": "local",
     "command": ["node", "scripts/mcp-servers/<name>-mcp.mjs"],
     "environment": {
       "<NAME>_API_KEY": "value"
     }
   }
   ```

4. **Test** — Restart OpenCode and invoke the tools from a conversation.

5. **Update memory** — Add the new MCP server to `memory/index.md` under Skills active or Active projects.

## Server template

```js
#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const API_KEY = process.env.<NAME>_API_KEY || "";
const BASE_URL = "https://api.example.com";

// ── Tool definitions ──────────────────────────────────────────────────────

const TOOLS = [
  {
    name: "<name>_<action>",
    description: "What this tool does",
    inputSchema: {
      type: "object",
      properties: {
        // define parameters
      },
    },
  },
];

// ── API helpers ───────────────────────────────────────────────────────────

async function apiFetch(path, params = {}) {
  const url = new URL(path, BASE_URL);
  for (const [k, v] of Object.entries(params)) {
    url.searchParams.set(k, String(v));
  }
  const res = await fetch(url.toString(), {
    headers: API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {},
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

function formatResult(data) {
  // transform API response to readable markdown-ish text
  return JSON.stringify(data, null, 2);
}

// ── MCP server ────────────────────────────────────────────────────────────

const server = new Server(
  { name: "<name>", version: "1.0.0" },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOLS,
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const tool = TOOLS.find((t) => t.name === name);

  if (!tool) {
    return {
      content: [{ type: "text", text: `Unknown tool: ${name}` }],
      isError: true,
    };
  }

  try {
    const data = await apiFetch(/* path based on tool */, args || {});
    return {
      content: [{ type: "text", text: formatResult(data) }],
    };
  } catch (err) {
    return {
      content: [{ type: "text", text: `Error: ${err.message}` }],
      isError: true,
    };
  }
});

// ── Start ─────────────────────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);
```

## Existing servers for reference

| Server | File | API | Tools |
|--------|------|-----|-------|
| Goodreads | `scripts/mcp-servers/goodreads-mcp.mjs` | Piratereads | 4 shelf tools |
| Granola | Remote (not local) | Granola MCP | Meeting notes, transcripts |

## Naming conventions

- File: `<service>-mcp.mjs` (e.g., `goodreads-mcp.mjs`, `notion-mcp.mjs`)
- Tool names: `<service>_<action>` (e.g., `goodreads_currently_reading`)
- Config key in opencode.json: matches the service name
- Env vars: `<SERVICE>_API_KEY` or `<SERVICE>_USER_ID` — uppercase, service-prefixed

## Gotchas

- The SDK is installed at `scripts/mcp-servers/node_modules/`, so server files must live in that directory or reference it correctly.
- Stdio transport means the server communicates over stdin/stdout — don't use `console.log()` for debugging (it pollutes the MCP channel). Use `console.error()` instead.
- Pagination: always support `page` and `per_page` parameters if the API paginates.
- Errors: always return `{ isError: true }` in the MCP response for API failures — don't throw unhandled.
