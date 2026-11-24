import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { basename, join, resolve } from "node:path";

const JOB_EXT = /\.(ya?ml)$/i;

/**
 * The job files the cron runner installs, per ~/.moraine/cron/enabled.json
 * (written by `moraine sync`). Paths are relative to the workspace root.
 */
export function readEnabledJobs(enabledFile: string): string[] {
  try {
    const data = JSON.parse(readFileSync(enabledFile, "utf-8"));
    return Array.isArray(data.jobs) ? data.jobs : [];
  } catch {
    return [];
  }
}

/** Basenames of every job shipped in the repo's packs (including `local`). */
function shippedJobNames(workspaceRoot: string): Set<string> {
  const names = new Set<string>();
  try {
    for (const pack of readdirSync(join(workspaceRoot, "packs"), { withFileTypes: true })) {
      if (!pack.isDirectory()) continue;
      const jobsDir = join(workspaceRoot, "packs", pack.name, "jobs");
      if (!existsSync(jobsDir)) continue;
      for (const job of readdirSync(jobsDir)) {
        if (JOB_EXT.test(job)) names.add(job);
      }
    }
  } catch {
    // No packs dir (or unreadable) → nothing is shipped, so nothing is stale.
  }
  return names;
}

/**
 * Make targetDir hold exactly the enabled jobs: copy each one in, then
 * remove installed files that match a shipped job no longer enabled. Files
 * that do not match any shipped job are left alone — they are the user's.
 */
export function installEnabled(enabledFile: string, targetDir: string, workspaceRoot: string): number {
  const enabled = readEnabledJobs(enabledFile);
  mkdirSync(targetDir, { recursive: true });

  let count = 0;
  for (const job of enabled) {
    const source = resolve(workspaceRoot, job);
    if (!existsSync(source)) {
      console.log(`  Missing ${job} (listed in ${basename(enabledFile)}) — skipped`);
      continue;
    }
    copyFileSync(source, join(targetDir, basename(job)));
    count++;
  }

  const shipped = shippedJobNames(workspaceRoot);
  const enabledNames = new Set(enabled.map((job) => basename(job)));
  for (const entry of readdirSync(targetDir)) {
    if (!JOB_EXT.test(entry)) continue;
    if (shipped.has(entry) && !enabledNames.has(entry)) {
      rmSync(join(targetDir, entry));
      console.log(`  Removed ${entry} (no longer enabled)`);
    }
  }

  console.log(`Installed ${count} job(s) to ${targetDir}`);
  return count;
}
