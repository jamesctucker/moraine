import { homedir } from "node:os";
import { join, resolve } from "node:path";

export function expandTilde(raw: string): string {
  if (raw.startsWith("~/")) {
    return join(homedir(), raw.slice(2));
  }
  return raw;
}

export function resolvePath(raw: string, workspaceRoot: string): string {
  const expanded = expandTilde(raw);
  if (expanded.startsWith("/")) return expanded;
  return resolve(workspaceRoot, expanded);
}
