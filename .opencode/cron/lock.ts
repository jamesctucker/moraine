import {
  openSync,
  writeSync,
  closeSync,
  readFileSync,
  unlinkSync,
  mkdirSync,
  linkSync,
  renameSync,
} from "node:fs";
import { join } from "node:path";
import { randomBytes } from "node:crypto";

/**
 * Job names become lock file names, so they are restricted to a bounded
 * slug: no path separators, no traversal, nothing header-hostile.
 */
export const LOCK_KEY_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;

function pidAlive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function uniqueSuffix(): string {
  return `${process.pid}-${randomBytes(6).toString("hex")}`;
}

/** Reads the owning pid recorded in a lock file; null when unreadable. */
function readOwner(lockPath: string): number | null {
  try {
    const raw = readFileSync(lockPath, "utf-8").trim();
    if (!/^\d+$/.test(raw) || raw === "0") return null;
    return parseInt(raw, 10);
  } catch {
    return null;
  }
}

/**
 * Creates the lock file with this process as owner. The owner pid is
 * written to a uniquely-named temp file first and hard-linked into place,
 * so the lock file never exists half-written for a racing process to
 * mistake for a stale one.
 */
function tryLinkOwner(lockPath: string): boolean {
  const tmpPath = `${lockPath}.${uniqueSuffix()}.tmp`;
  try {
    const fd = openSync(tmpPath, "wx");
    writeSync(fd, String(process.pid));
    closeSync(fd);
    linkSync(tmpPath, lockPath);
    return true;
  } catch (err) {
    const e = err as NodeJS.ErrnoException;
    if (e.code !== "EEXIST") {
      console.warn(`Warning: could not acquire lock at ${lockPath}: ${e.message}`);
    }
    return false;
  } finally {
    try { unlinkSync(tmpPath); } catch { /* never created or already linked */ }
  }
}

/**
 * Atomically claims a lock file we believe is stale by renaming it under
 * a unique name — exactly one of several racing reapers can win. If the
 * claimed file turns out not to hold the content we saw (a fresh owner
 * took over between our read and the rename), the claim is put back.
 *
 * Residual bound: a third contender can claim lockPath between a failed
 * restore and the claim unlink, losing the original owner's record. This
 * pid-file protocol cannot close that micro-window; an OS-held flock would
 * be required. Cron is single-user and local, so this remains an accepted
 * rare duplicate-execution risk rather than a silent correctness claim.
 */
function claimStaleLock(lockPath: string, observedOwner: number | null): boolean {
  const claimPath = `${lockPath}.${uniqueSuffix()}.reap`;
  try {
    renameSync(lockPath, claimPath);
  } catch {
    return false; // another reaper removed it first
  }
  if (readOwner(claimPath) !== observedOwner) {
    // We renamed away a live owner's lock — restore it.
    try {
      linkSync(claimPath, lockPath);
    } catch {
      // Someone else already owns lockPath; the claimed copy is obsolete.
    }
    try { unlinkSync(claimPath); } catch { /* ignore */ }
    return false;
  }
  try { unlinkSync(claimPath); } catch { /* ignore */ }
  return true;
}

export function acquireLock(jobName: string, locksDir: string): boolean {
  if (!LOCK_KEY_PATTERN.test(jobName)) {
    console.warn(`Warning: refusing lock for invalid job name '${jobName}'`);
    return false;
  }
  mkdirSync(locksDir, { recursive: true });
  const lockPath = join(locksDir, `${jobName}.pid`);

  for (let attempt = 0; attempt < 3; attempt++) {
    if (tryLinkOwner(lockPath)) return true;

    const owner = readOwner(lockPath);
    if (owner !== null && pidAlive(owner)) return false;

    if (!claimStaleLock(lockPath, owner)) continue; // lost the reaping race
    if (tryLinkOwner(lockPath)) return true;
  }
  return false;
}

export function releaseLock(jobName: string, locksDir: string): void {
  const lockPath = join(locksDir, `${jobName}.pid`);
  try {
    // Compare-before-unlink: never remove a lock file this process
    // doesn't own (e.g. one a reaper already handed to a new owner).
    if (readOwner(lockPath) !== process.pid) return;
    unlinkSync(lockPath);
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code !== "ENOENT") throw e;
  }
}
