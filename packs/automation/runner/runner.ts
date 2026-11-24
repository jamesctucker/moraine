#!/usr/bin/env bun
import { join, resolve } from "node:path";
import { readdirSync } from "node:fs";
import { hostname } from "node:os";
import { fileURLToPath } from "node:url";
import { loadConfig } from "./config";
import { loadJobs, buildPrompt } from "./job";
import { matches } from "./scheduler";
import { acquireLock, releaseLock } from "./lock";
import { runWithTimeout } from "./spawn";
import { routeOutput } from "./output";
import { sendJobEmail } from "./email";
import { createLogger } from "./logger";
import { installEnabled } from "./install";
import { resolvePath } from "./util";
import type { CronConfig, Job, RunResult } from "./types";

const WORKSPACE_ROOT = resolve(fileURLToPath(new URL(".", import.meta.url)), "../../..");

function parseArgs(args: string[]) {
  const list = args.includes("--list");
  const dryRun = args.includes("--dry-run");
  const installDefaults = args.includes("--install-defaults");

  const onceIndex = args.indexOf("--once");
  const once = onceIndex !== -1 && args[onceIndex + 1] && !args[onceIndex + 1].startsWith("-")
    ? args[onceIndex + 1]
    : null;

  const jobDirIndex = args.indexOf("--job-dir");
  const jobDir = jobDirIndex !== -1 && args[jobDirIndex + 1] && !args[jobDirIndex + 1].startsWith("-")
    ? args[jobDirIndex + 1]
    : null;

  return { list, dryRun, installDefaults, once, jobDir };
}

/** Run one job and preserve its log even when output routing fails. */
export async function runJob(job: Job, config: CronConfig, dryRun: boolean): Promise<number> {
  if (dryRun) {
    const model = job.model ?? config.default.model ?? "(opencode default)";
    const timeout = job.timeout ?? config.default.timeout;
    console.log(`  [${job.name}] DRY RUN`);
    console.log(`    model: ${model}`);
    console.log(`    timeout: ${timeout}s`);
    if (job.agent) console.log(`    agent: ${job.agent}`);
    if (job.skills?.length) console.log(`    skills: ${job.skills.join(", ")}`);
    if (job.output) console.log(`    output: ${job.output}`);
    if (job.email) console.log(`    email: ${job.email.to}`);
    if (job.prepend) console.log(`    mode: prepend`);
    else if (job.append) console.log(`    mode: append`);
    else if (job.output) console.log(`    mode: write`);
    return 0;
  }

  const locksDir = resolvePath(config.locks_dir, WORKSPACE_ROOT);

  if (!acquireLock(job.name, locksDir)) {
    return -1;
  }

  const logger = createLogger(job.name, resolvePath(config.log_dir, WORKSPACE_ROOT));
  const model = job.model ?? config.default.model ?? "";
  const timeout = job.timeout ?? config.default.timeout;

  try {
    const env: Record<string, string> = {};
    // Strip session-binding env when spawning headless runs: a runner invoked
    // from inside a bound agent session would otherwise leak
    // OPENCODE_CONFIG_CONTENT (the host's plugin + runtime token) into the child,
    // whose Bash tool then dies with a "not bound to an agent" error.
    const BLOCKED_PREFIXES = ["PASEO_", "OPENCODE_CONFIG", "OPENCODE_PID"];
    for (const [k, v] of Object.entries(process.env)) {
      if (v === undefined) continue;
      if (BLOCKED_PREFIXES.some((p) => k.startsWith(p))) continue;
      env[k] = v;
    }
    delete env["OPENCODE"];
    env["OPENCODE_DISABLE_AUTOUPDATE"] = "true";

    const cmdArgs = ["run", "--title", job.name];
    if (model) cmdArgs.push("--model", model);
    if (job.agent) cmdArgs.push("--agent", job.agent);
    cmdArgs.push(buildPrompt(job));

    // Stream child output live while buffering it for output routing and
    // email delivery. execFileSync would hide all progress for minutes
    // (the job scans ~100 session files before printing anything).
    const result = await runWithTimeout("opencode", cmdArgs, {
      timeout,
      env,
      onStdout: (d) => process.stdout.write(d),
      onStderr: (d) => process.stderr.write(d),
    });

    let stderr = result.stderr;
    if (result.timedOut) stderr += `\n[killed after ${timeout}s timeout]`;
    const runResult: RunResult = {
      exitCode: result.exitCode ?? 1,
      stdout: result.stdout,
      stderr,
      duration: result.duration,
    };

    if (runResult.exitCode !== 0) {
      const previewLines = runResult.stdout
        .trim()
        .split("\n")
        .filter(Boolean)
        .concat(runResult.stderr.trim().split("\n").filter(Boolean));
      logger.writeToConsole("FAILED", previewLines);
      const logPath = logger.writeLogFile(runResult, model);
      console.log(`    log: ${logPath}`);
      return runResult.exitCode;
    }

    let outputError: Error | null = null;
    try {
      const routed = await routeOutput(runResult.stdout.trim(), job, WORKSPACE_ROOT, { locksDir });
      if (routed) console.log(`    written: ${routed}`);
    } catch (e) {
      outputError = e as Error;
      runResult.exitCode = 1;
      runResult.stderr += `\n[output routing failed: ${outputError.message}]`;
      console.warn(`    output failed: ${outputError.message}`);
    }

    if (job.email && !outputError) {
      try {
        sendJobEmail(job.email, job.name, runResult.stdout.trim());
        console.log(`    emailed: ${job.email.to}`);
      } catch (e) {
        // Email delivery failure must not fail the job — the output is
        // already routed/logged, and email is the notification layer.
        console.warn(`    email failed: ${(e as Error).message}`);
      }
    }

    const previewLines = runResult.stdout.trim().split("\n").filter(Boolean).slice(0, 3);
    logger.writeToConsole(outputError ? "FAILED" : "OK", previewLines);
    const logPath = logger.writeLogFile(runResult, model);

    if (outputError || runResult.stdout.trim().split("\n").filter(Boolean).length > 3) {
      console.log(`    log: ${logPath}`);
    }
    return outputError ? 1 : 0;
  } finally {
    releaseLock(job.name, locksDir);
  }
}

function localHostname(): string {
  // macOS Computer Names can carry trailing whitespace
  // ("John's MacBook Air ") — trim so YAML hostnames can be written cleanly.
  return hostname().split(".")[0].trim();
}

function listJobs(jobs: Job[], config: CronConfig): void {
  const h = localHostname();
  console.log(`\nCron jobs (hostname: ${h}):\n`);
  console.log(`  ${"NAME".padEnd(30)} ${"SCHEDULE".padEnd(20)} ${"MODEL".padEnd(30)} ${"OUTPUT"}`);
  console.log(`  ${"".padEnd(30, "-")} ${"".padEnd(20, "-")} ${"".padEnd(30, "-")} ${"".padEnd(40, "-")}`);

  for (const job of jobs) {
    const model = job.model ?? config.default.model ?? "(default)";
    const output = job.output ?? "";
    const mode = job.prepend ? " (prepend)" : job.append ? " (append)" : "";
    const hostOk = !job.hostname || job.hostname === h;
    let status = !hostOk ? " (host skip)" : job.disabled ? " (disabled)" : "";
    if (job.email) status += " [emails]";
    console.log(`  ${job.name.padEnd(30)} ${job.cron.padEnd(20)} ${model.padEnd(30)} ${(output + mode).padEnd(40)}${status}`);
  }
  console.log();
}

async function main(): Promise<number> {
  const args = parseArgs(process.argv.slice(2));

  const configPath = resolve(WORKSPACE_ROOT, "packs/automation/runner/cron.config.yaml");
  const config = loadConfig(configPath);
  const installDir = resolvePath(config.install_dir, WORKSPACE_ROOT);
  // enabled.json (written by `moraine sync`) names the jobs to install; it
  // lives in the install dir alongside the job files.
  const enabledFile = join(installDir, "enabled.json");

  if (args.installDefaults) {
    installEnabled(enabledFile, installDir, WORKSPACE_ROOT);
    return 0;
  }

  const jobDir = args.jobDir ? resolvePath(args.jobDir, WORKSPACE_ROOT) : installDir;

  // The install dir also holds enabled.json, so "empty" means no job files.
  const hasJobFiles = (dir: string) => {
    try {
      return readdirSync(dir).some((entry) => /\.(ya?ml)$/i.test(entry));
    } catch {
      return false;
    }
  };

  if (!args.jobDir && !hasJobFiles(jobDir)) {
    console.log(`Cron directory '${jobDir}' has no job files. Installing from the enabled list...`);
    installEnabled(enabledFile, jobDir, WORKSPACE_ROOT);
  }

  const jobs = loadJobs(jobDir);

  if (!jobs.length) {
    console.log("No jobs found.");
    return 1;
  }

  if (args.list) {
    listJobs(jobs, config);
    return 0;
  }

  if (args.once) {
    const matched = jobs.filter(j => j.name === args.once);
    if (!matched.length) {
      console.log(`Job '${args.once}' not found.`);
      return 1;
    }
    return await runJob(matched[0], config, args.dryRun);
  }

  const now = new Date();
  const matchedJobs = jobs.filter(j => matches(j.cron, now));

  if (!matchedJobs.length) {
    console.log(`No jobs match the current time (${now.toISOString().slice(0, 16).replace("T", " ")}).`);
    return 0;
  }

  const h = localHostname();
  let exitCode = 0;
  for (const job of matchedJobs) {
    if (job.disabled) {
      console.log(`  [${job.name}] SKIPPED (disabled)`);
      continue;
    }
    if (job.hostname && job.hostname !== h) {
      console.log(`  [${job.name}] SKIPPED (hostname restriction)`);
      continue;
    }
    const rc = await runJob(job, config, args.dryRun);
    if (rc === -1) {
      console.log(`  [${job.name}] SKIPPED (lock held by another process)`);
    } else if (rc !== 0) {
      exitCode = rc;
    }
  }

  return exitCode;
}

if (import.meta.main) {
  main()
    .then(code => process.exit(code))
    .catch(err => {
      console.error("Fatal:", err);
      process.exit(1);
    });
}
