import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { basename, join, resolve } from "node:path";

const JOB_EXT = /\.(ya?ml)$/i;

/**
 * The job files the cron runner installs, per ~/.moraine/cron/enabled.json
 * (written by `moraine sync`). Paths are relative to the workspace root.
 * A missing file means sync has not run (or the runner pack is disabled);
 * a file that exists but does not parse is corrupt state and throws, so a
 * bad enabled list can never look like "no jobs" and uninstall everything.
 */
export function readEnabledJobs(enabledFile: string): string[] {
  let raw: string;
  try {
    raw = readFileSync(enabledFile, "utf-8");
  } catch {
    return [];
  }
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    throw new Error(`${enabledFile} is not valid JSON — fix or delete it (moraine sync rewrites it): ${(e as Error).message}`);
  }
  const jobs = (data as { jobs?: unknown }).jobs;
  if (!Array.isArray(jobs) || !jobs.every((job) => typeof job === "string")) {
    throw new Error(`${enabledFile} must hold {"jobs": [string, ...]} — fix or delete it (moraine sync rewrites it)`);
  }
  return jobs;
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
