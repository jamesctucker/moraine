# Security Policy

## Supported versions

Only the latest release line (currently 0.3.x) receives security fixes.

## Trust model — read this first

Moraine runs an AI coding agent against files in your workspace. Keep these boundaries in mind before reporting something as a vulnerability:

- **Skills and config are instructions your agent follows.** Review upstream changes before syncing (`docs/upstream-sync.md`). A malicious upstream skill is a supply-chain issue, not a Moraine sandbox escape — there is no OS-level sandbox.
- **OpenCode permission rules are not a sandbox.** The deny/ask lists in `opencode.json` gate commands; they do not isolate file or network access at the OS level.
- **Your model provider and MCP servers see what you send them.** Their data policies apply, not Moraine's.
- **Moraine is for personal workspaces.** Employer-confidential code, customer data, credentials, and NDA material do not belong in it. Deterministic scanning (secret scanning, credential hooks) is a backstop for known secret patterns, not a detector for arbitrary confidential prose or source code.

## Reporting a vulnerability

Use [GitHub's private vulnerability reporting](https://github.com/jamesctucker/moraine/security/advisories/new) ("Report a vulnerability"). Please include reproduction steps and affected versions. Don't open a public issue for anything exploitable.

Please give a reasonable window (aim for 90 days) before public disclosure.
