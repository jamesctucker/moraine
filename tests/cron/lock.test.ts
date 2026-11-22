import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { acquireLock, releaseLock } from "../../.opencode/cron/lock";
import { existsSync, mkdirSync, rmSync, writeFileSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { fixtureRuntime, startWorker } from "./helpers";

const WORKER = fileURLToPath(new URL("./fixtures/lock-worker.mjs", import.meta.url));

describe("lock.ts", () => {
  const locksDir = join(tmpdir(), `cron-test-locks-${Date.now()}`);

  beforeAll(() => {
    mkdirSync(locksDir, { recursive: true });
  });

  afterAll(() => {
    rmSync(locksDir, { recursive: true, force: true });
  });

  it("should acquire and release a lock", () => {
    const acquired = acquireLock("test-lock", locksDir);
    expect(acquired).toBe(true);

    const lockPath = join(locksDir, "test-lock.pid");
    expect(existsSync(lockPath)).toBe(true);
    // Atomic acquisition records the owner immediately — never an
    // empty file another process could mistake for a stale lock.
    expect(readFileSync(lockPath, "utf-8").trim()).toBe(String(process.pid));

    releaseLock("test-lock", locksDir);
    expect(existsSync(lockPath)).toBe(false);
  });

  it("should block concurrent acquire", () => {
    acquireLock("concurrent-test", locksDir);
    const secondAcquire = acquireLock("concurrent-test", locksDir);
    expect(secondAcquire).toBe(false);
    // A failed contender must not have touched the owner's lock.
    expect(readFileSync(join(locksDir, "concurrent-test.pid"), "utf-8").trim())
      .toBe(String(process.pid));

    releaseLock("concurrent-test", locksDir);
  });

  it("should reap stale locks", () => {
    // Write a lock file with a dead PID — 8 digits is beyond any
    // platform's pid_max, so it can never be alive.
    const lockPath = join(locksDir, "stale-lock.pid");
    writeFileSync(lockPath, "99999999");
    const acquired = acquireLock("stale-lock", locksDir);
    expect(acquired).toBe(true);

    releaseLock("stale-lock", locksDir);
  });

  it("should reap an empty lock file left by a crashed writer", () => {
    const lockPath = join(locksDir, "empty-lock.pid");
    writeFileSync(lockPath, "");
    expect(acquireLock("empty-lock", locksDir)).toBe(true);

    releaseLock("empty-lock", locksDir);
  });

  it("should reap a lock file with garbage content", () => {
    writeFileSync(join(locksDir, "garbage-lock.pid"), "not-a-pid");
    expect(acquireLock("garbage-lock", locksDir)).toBe(true);

    releaseLock("garbage-lock", locksDir);
  });

  it("releaseLock should not throw on missing lock", () => {
    expect(() => releaseLock("nonexistent", locksDir)).not.toThrow();
  });

  it("releaseLock should not remove a lock owned by another process", () => {
    acquireLock("foreign-owner", locksDir);
    const lockPath = join(locksDir, "foreign-owner.pid");
    // A reaper handed the lock to a new owner while our job ran.
    writeFileSync(lockPath, "4194300");
    releaseLock("foreign-owner", locksDir);
    expect(existsSync(lockPath)).toBe(true);

    rmSync(lockPath);
  });

  it("should refuse lock keys that are not slugs", () => {
    expect(acquireLock("../escape", locksDir)).toBe(false);
    expect(acquireLock("a/b", locksDir)).toBe(false);
    expect(acquireLock("bad name", locksDir)).toBe(false);
    expect(acquireLock("x".repeat(65), locksDir)).toBe(false);
    // No lock files for the refused names, inside or outside the dir.
    expect(readdirSync(locksDir).some(f => f.includes("escape"))).toBe(false);
    expect(existsSync(join(tmpdir(), "escape.pid"))).toBe(false);
  });
});

describe("lock.ts multiprocess", () => {
  const locksDir = join(tmpdir(), `cron-test-locks-mp-${Date.now()}`);

  beforeAll(() => {
    mkdirSync(locksDir, { recursive: true });
  });

  afterAll(() => {
    rmSync(locksDir, { recursive: true, force: true });
  });

  it("exactly one of several racing processes acquires a fresh lock", async () => {
    const workers = Array.from({ length: 6 }, () => startWorker(WORKER, ["mp-fresh", locksDir]));
    try {
      await Promise.all(workers.map(w => w.waitFor("ready")));
      // Barrier: release every worker onto the lock at once.
      for (const w of workers) w.send("acquire");

      const answers = await Promise.all(workers.map(w => w.waitFor("acquired")));
      expect(answers.filter(a => a.endsWith("true"))).toHaveLength(1);

      // The lock file names the winner, and only the winner.
      const owner = parseInt(readFileSync(join(locksDir, "mp-fresh.pid"), "utf-8"), 10);
      expect(workers.some(w => w.pid === owner)).toBe(true);

      // The winner can hand the lock on.
      const winner = workers.find(w => w.pid === owner)!;
      winner.send("release");
      await winner.waitFor("released");
      expect(acquireLock("mp-fresh", locksDir)).toBe(true);
      releaseLock("mp-fresh", locksDir);
    } finally {
      for (const w of workers) w.kill();
    }
  }, 30_000);

  it("exactly one of several racing processes reaps a stale lock", async () => {
    // A genuinely dead owner: spawn a real process and wait it out.
    const [runtimeCmd, ...runtimeArgs] = fixtureRuntime();
    const dead = spawn(runtimeCmd, [...runtimeArgs, "--version"]);
    const deadPid = dead.pid!;
    await new Promise<void>(resolve => dead.on("close", () => resolve()));
    writeFileSync(join(locksDir, "mp-stale.pid"), String(deadPid));

    const workers = Array.from({ length: 6 }, () => startWorker(WORKER, ["mp-stale", locksDir]));
    try {
      await Promise.all(workers.map(w => w.waitFor("ready")));
      for (const w of workers) w.send("acquire");

      const answers = await Promise.all(workers.map(w => w.waitFor("acquired")));
      expect(answers.filter(a => a.endsWith("true"))).toHaveLength(1);

      const owner = parseInt(readFileSync(join(locksDir, "mp-stale.pid"), "utf-8"), 10);
      expect(owner).not.toBe(deadPid);
      expect(workers.some(w => w.pid === owner)).toBe(true);
    } finally {
      for (const w of workers) w.kill();
    }
  }, 30_000);
});
