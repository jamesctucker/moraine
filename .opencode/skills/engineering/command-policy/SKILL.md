---
name: command-policy
description: Safety policy for bash command execution. Blocks destructive patterns (rm -rf /, dd, mkfs, writes outside repo). Use when executing any bash command to ensure safe command construction.
---

# Command Policy

This skill enforces a safety policy for all bash command execution. It blocks destructive patterns and requires confirmation for operations outside the workspace.

## Policy Rules

### 1. Block destructive patterns

Never construct commands containing these patterns. If you detect a match in your own command before executing, stop and inform the user:

| Pattern | Reason |
|---------|--------|
| `rm -rf /` or `rm -rf /*` | Recursive root deletion |
| `rm -rf ~` or `rm -rf $HOME` | Home directory deletion |
| `dd if=` with block device target (`of=/dev/sd*`) | Disk destruction |
| `mkfs`, `mkswap`, `fdisk` on block devices | Filesystem destruction |
| `> /dev/sd*`, `> /dev/nvme*` | Direct block device write |
| `chmod -R 777 /` or `chown -R` on root | Mass permission reset |
| `:(){ :|:& };:` | Fork bomb |
| `wget`/`curl` piping to `sh` or `bash` without verification | Arbitrary remote execution |

### 2. Confirm writes outside the workspace

Any command that creates or modifies files outside `WORKSPACE` (this workspace's root) must be flagged for user confirmation before execution. Explicitly state the external path and ask.

### 3. Prefer safe alternatives

- Use `/tmp/opencode` for temporary files (already exists, pre-approved)
- Use `mkdir -p` over bare `mkdir`
- Prepend `ls` / `stat` before destructive operations to confirm the target
- Use `$(pwd)/` for workspace-relative paths rather than absolute paths

### 4. Integration with sandbox

The `scripts/sandbox/opencode-sandbox` wrapper provides runtime enforcement:

- **`opencode-sandbox lite`**: creates a git checkpoint before the session, runs a diff review and PII scan on exit
- **`opencode-sandbox full`**: adds Apple sandbox-exec with filesystem scope restrictions

When a sandbox wrapper is available, prefer running commands inside it.

## Workflow

Before running any bash command:

1. **Scan** the command string for the destructive patterns in Rule 1
2. **Check** whether any file targets lie outside `WORKSPACE`
3. **Block or confirm** — destructive patterns are blocked unconditionally; out-of-repo writes require user approval
4. **Execute** with the `bash` tool
