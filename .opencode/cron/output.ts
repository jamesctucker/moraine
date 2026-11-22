import { existsSync, readFileSync, writeFileSync, mkdirSync, renameSync, unlinkSync } from "node:fs";
import { dirname, join } from "node:path";
import { createHash, randomBytes } from "node:crypto";
import { tmpdir } from "node:os";
import { parse as parseYaml, stringify as stringifyYaml } from "yaml";
import { acquireLock, releaseLock } from "./lock";
import { resolvePath } from "./util";
import type { Job } from "./types";

interface Frontmatter {
  [key: string]: unknown;
}

export interface OutputRouteOptions {
  /** Directory holding the per-path output locks. */
  locksDir?: string;
  /** How long to wait for a contended output lock before failing. */
  lockWaitMs?: number;
}

const DEFAULT_LOCK_WAIT_MS = 10_000;
const LOCK_POLL_MS = 100;

function parseFrontmatter(content: string): { frontmatter: Frontmatter | null; body: string } {
  const match = content.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!match) return { frontmatter: null, body: content.trimEnd() };

  try {
    const frontmatter = parseYaml(match[1]);
    if (typeof frontmatter === "object" && frontmatter !== null) {
      return { frontmatter: frontmatter as Frontmatter, body: match[2].trimEnd() };
    }
  } catch {
    // invalid YAML — treat as no frontmatter
  }
  return { frontmatter: null, body: content.trimEnd() };
}

function mergeFrontmatter(base: Frontmatter, overlay: Frontmatter): Frontmatter {
  const merged: Frontmatter = { ...base };

  for (const [key, value] of Object.entries(overlay)) {
    if (Array.isArray(value) && Array.isArray(merged[key])) {
      const existing = merged[key] as unknown[];
      const incoming = value as unknown[];
      merged[key] = [...existing];
      for (const item of incoming) {
        if (!existing.some(e => JSON.stringify(e) === JSON.stringify(item))) {
          (merged[key] as unknown[]).push(item);
        }
      }
    } else {
      merged[key] = value;
    }
  }

  return merged;
}

function buildWithFrontmatter(fm: Frontmatter, body: string): string {
  return `---\n${stringifyYaml(fm).trim()}\n---\n\n${body.trimEnd()}\n`;
}

function substituteDate(path: string): string {
  const now = new Date();
  const dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  return path.replace(/YYYY-MM-DD/g, dateStr);
}

function resolveOutputPath(outputPath: string, workspaceRoot: string): string {
  return resolvePath(substituteDate(outputPath), workspaceRoot);
}

function ensureParentDir(filePath: string): void {
  mkdirSync(dirname(filePath), { recursive: true });
}

/**
 * Locks are keyed by canonical output path, so two different jobs
 * targeting the same note serialize against each other — the per-job
 * lock alone cannot protect a shared output file.
 */
function outputLockKey(outputPath: string): string {
  const hash = createHash("sha256").update(outputPath).digest("hex").slice(0, 32);
  return `output-${hash}`;
}

async function acquireOutputLock(lockKey: string, locksDir: string, waitMs: number): Promise<boolean> {
  const deadline = Date.now() + waitMs;
  while (!acquireLock(lockKey, locksDir)) {
    if (Date.now() >= deadline) return false;
    await new Promise(resolve => setTimeout(resolve, LOCK_POLL_MS));
  }
  return true;
}

/** Writes via a same-directory temp file and an atomic rename, so a
 * reader never observes a truncated note. */
function atomicWrite(outputPath: string, data: string): void {
  const tmpPath = `${outputPath}.${process.pid}.${randomBytes(6).toString("hex")}.tmp`;
  try {
    writeFileSync(tmpPath, data, "utf-8");
    renameSync(tmpPath, outputPath);
  } catch (err) {
    try { unlinkSync(tmpPath); } catch { /* nothing was written */ }
    throw err;
  }
}

function prependOutput(outputPath: string, content: string): void {
  if (!existsSync(outputPath)) {
    atomicWrite(outputPath, content + "\n");
    return;
  }

  const existingContent = readFileSync(outputPath, "utf-8").trimEnd();
  const newParsed = parseFrontmatter(content);
  const existingParsed = parseFrontmatter(existingContent);
  if (!newParsed.frontmatter && !existingParsed.frontmatter) {
    atomicWrite(outputPath, content + "\n\n---\n\n" + existingContent + "\n");
    return;
  }

  const mergedFm = mergeFrontmatter(
    existingParsed.frontmatter ?? {},
    newParsed.frontmatter ?? {},
  );
  const merged = buildWithFrontmatter(
    mergedFm,
    newParsed.body + "\n\n---\n\n" + existingParsed.body,
  );
  atomicWrite(outputPath, merged);
}

function appendOutput(outputPath: string, content: string): void {
  if (!existsSync(outputPath)) {
    atomicWrite(outputPath, content + "\n");
    return;
  }
  const existingContent = readFileSync(outputPath, "utf-8").trimEnd();
  atomicWrite(outputPath, existingContent + "\n\n---\n\n" + content + "\n");
}

function writeOutput(outputPath: string, job: Job, content: string): void {
  if (job.prepend) {
    prependOutput(outputPath, content);
  } else if (job.append) {
    appendOutput(outputPath, content);
  } else {
    atomicWrite(outputPath, content + "\n");
  }
}

export async function routeOutput(
  content: string,
  job: Job,
  workspaceRoot: string,
  options: OutputRouteOptions = {},
): Promise<string | null> {
  if (!job.output) return null;

  const outputPath = resolveOutputPath(job.output, workspaceRoot);
  ensureParentDir(outputPath);

  const trimmedContent = content.trimEnd();

  const locksDir = options.locksDir ?? join(tmpdir(), "moraine-cron-output-locks");
  const lockKey = outputLockKey(outputPath);

  if (!await acquireOutputLock(lockKey, locksDir, options.lockWaitMs ?? DEFAULT_LOCK_WAIT_MS)) {
    throw new Error(`could not acquire output lock for ${outputPath} (held by another process)`);
  }

  try {
    writeOutput(outputPath, job, trimmedContent);
  } finally {
    releaseLock(lockKey, locksDir);
  }

  return outputPath;
}
