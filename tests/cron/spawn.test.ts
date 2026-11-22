import { describe, it, expect } from "vitest";
import { runWithTimeout } from "../../.opencode/cron/spawn";
import { fileURLToPath } from "node:url";

const FIXTURES = fileURLToPath(new URL("./fixtures", import.meta.url));

function pidAlive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

describe("runWithTimeout", () => {
  it("returns exit code and output for a completing child", async () => {
    const result = await runWithTimeout(
      process.execPath,
      ["-e", "console.log('hello from child')"],
      { timeout: 10 },
    );
    expect(result.exitCode).toBe(0);
    expect(result.timedOut).toBe(false);
    expect(result.stdout).toContain("hello from child");
  }, 15_000);

  it("reports a non-zero exit code", async () => {
    const result = await runWithTimeout(process.execPath, ["-e", "process.exit(3)"], { timeout: 10 });
    expect(result.exitCode).toBe(3);
  }, 15_000);

  it("reports spawn failures as exit code 1", async () => {
    const result = await runWithTimeout("definitely-not-a-real-binary-xyz", [], { timeout: 5 });
    expect(result.exitCode).toBe(1);
    expect(result.stderr).toContain("definitely-not-a-real-binary-xyz");
  }, 15_000);

  it("kills a SIGTERM-trapping child with SIGKILL after the grace period", async () => {
    const result = await runWithTimeout(process.execPath, [`${FIXTURES}/sigterm-trap.mjs`], {
      timeout: 0.3,
      killGrace: 0.3,
    });
    expect(result.timedOut).toBe(true);
    expect(result.exitCode).toBeNull();
    expect(result.signal).toBe("SIGKILL");
    // The child received — and trapped — the first SIGTERM.
    expect(result.stdout).toContain("SIGTERM trapped");
    // And it is genuinely gone afterwards.
    const pid = parseInt(result.stdout.match(/pid (\d+)/)![1], 10);
    expect(pidAlive(pid)).toBe(false);
  }, 15_000);

  it("clears a surviving grandchild holding the pipes (group SIGKILL)", async () => {
    const result = await runWithTimeout(process.execPath, [`${FIXTURES}/grandchild-spawner.mjs`], {
      timeout: 0.3,
      killGrace: 0.3,
    });
    // The direct child exited successfully before the timeout; the
    // grandchild it left holding the pipe is what had to be removed.
    expect(result.timedOut).toBe(true);
    expect(result.exitCode).toBe(0);
    const grand = parseInt(result.stdout.match(/grand (\d+)/)![1], 10);
    expect(pidAlive(grand)).toBe(false);
  }, 15_000);

  it("settles even when a grandchild escapes the process group", async () => {
    const result = await runWithTimeout(process.execPath, [`${FIXTURES}/rogue-grandchild-spawner.mjs`], {
      timeout: 0.3,
      killGrace: 0.3,
    });
    expect(result.timedOut).toBe(true);
    // Settled without a close event: the exit status is unknown.
    expect(result.exitCode).toBeNull();
    // The rogue grandchild survived the group kill (and holds the pipe).
    const rogue = parseInt(result.stdout.match(/grand (\d+)/)![1], 10);
    const escaped = pidAlive(rogue);
    process.kill(rogue, "SIGKILL");
    expect(escaped).toBe(true);
  }, 15_000);
});
