import { spawn } from "node:child_process";

export interface CommandResult {
  exitCode: number | null;
  signal: NodeJS.Signals | null;
  stdout: string;
  stderr: string;
  duration: number;
  timedOut: boolean;
}

export interface RunWithTimeoutOptions {
  /** Seconds before the watchdog starts terminating the job. */
  timeout: number;
  /** Seconds of grace between SIGTERM and SIGKILL. */
  killGrace?: number;
  env?: Record<string, string>;
  onStdout?: (chunk: Buffer) => void;
  onStderr?: (chunk: Buffer) => void;
}

const DEFAULT_KILL_GRACE_SECONDS = 10;
/** Final window after SIGKILL before settling without a close event —
 * a grandchild outside the process group can keep the pipes open. */
const SETTLE_MS = 1000;

/**
 * Runs a command to completion under a hard timeout. The child gets its
 * own process group so the watchdog can terminate the whole job tree:
 * SIGTERM first, SIGKILL after killGrace, and the promise settles even
 * if a surviving grandchild keeps the stdio pipes open.
 */
export function runWithTimeout(
  command: string,
  args: string[],
  options: RunWithTimeoutOptions,
): Promise<CommandResult> {
  const { timeout, env, onStdout, onStderr } = options;
  const graceMs = (options.killGrace ?? DEFAULT_KILL_GRACE_SECONDS) * 1000;
  const startTime = performance.now();

  return new Promise((resolve) => {
    const child = spawn(command, args, {
      env,
      stdio: ["ignore", "pipe", "pipe"],
      detached: true,
    });

    let stdout = "";
    let stderr = "";
    let timedOut = false;
    let settled = false;
    let killTimer: NodeJS.Timeout | undefined;
    let settleTimer: NodeJS.Timeout | undefined;

    const finish = (exitCode: number | null, signal: NodeJS.Signals | null) => {
      if (settled) return;
      settled = true;
      clearTimeout(watchdog);
      if (killTimer) clearTimeout(killTimer);
      if (settleTimer) clearTimeout(settleTimer);
      resolve({
        exitCode,
        signal,
        stdout,
        stderr,
        duration: Math.round((performance.now() - startTime) / 1000),
        timedOut,
      });
    };

    const signalTree = (signal: NodeJS.Signals) => {
      // The negative pid targets the child's whole process group.
      if (child.pid !== undefined) {
        try { process.kill(-child.pid, signal); } catch { /* group already gone */ }
      }
      try { child.kill(signal); } catch { /* already dead */ }
    };

    const watchdog = setTimeout(() => {
      timedOut = true;
      signalTree("SIGTERM");
      killTimer = setTimeout(() => {
        signalTree("SIGKILL");
        settleTimer = setTimeout(() => {
          finish(null, null);
        }, SETTLE_MS);
      }, graceMs);
    }, timeout * 1000);

    child.stdout.on("data", (d: Buffer) => {
      stdout += d.toString();
      onStdout?.(d);
    });
    child.stderr.on("data", (d: Buffer) => {
      stderr += d.toString();
      onStderr?.(d);
    });

    child.on("error", (err) => {
      if (!stderr) stderr = String(err);
      finish(1, null);
    });

    child.on("close", (code, signal) => finish(code, signal));
  });
}
