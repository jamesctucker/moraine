import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { routeOutput } from "../../.opencode/cron/output";
import { writeFileSync, readFileSync, existsSync, mkdirSync, rmSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import { acquireLock, releaseLock } from "../../.opencode/cron/lock";
import { startWorker } from "./helpers";
import type { Job } from "../../.opencode/cron/types";

const OUTPUT_WORKER = fileURLToPath(new URL("./fixtures/output-worker.mjs", import.meta.url));

describe("output.ts", () => {
  const tmpDir = join(tmpdir(), `cron-test-output-${Date.now()}`);
  const locksDir = join(tmpDir, "locks");

  beforeAll(() => {
    mkdirSync(tmpDir, { recursive: true });
  });

  afterAll(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  function makeJob(overrides: Partial<Job> = {}): Job {
    return {
      name: "test-job",
      cron: "* * * * *",
      prompt: "test",
      ...overrides,
    };
  }

  it("should write content to a new file", async () => {
    const path = join(tmpDir, "write-test.md");
    const job = makeJob({ output: path });
    await routeOutput("Hello world", job, tmpDir, { locksDir });
    expect(readFileSync(path, "utf-8")).toBe("Hello world\n");
  });

  it("should append content to an existing file", async () => {
    const path = join(tmpDir, "append-test.md");
    writeFileSync(path, "existing content\n");
    const job = makeJob({ output: path, append: true });
    await routeOutput("new content", job, tmpDir, { locksDir });
    const content = readFileSync(path, "utf-8");
    expect(content).toContain("existing content");
    expect(content).toContain("new content");
    expect(content).toContain("---");
  });

  it("should prepend content to a new file", async () => {
    const path = join(tmpDir, "prepend-new.md");
    const job = makeJob({ output: path, prepend: true });
    await routeOutput("## Morning Briefing\n\n- item 1", job, tmpDir, { locksDir });
    expect(readFileSync(path, "utf-8")).toContain("## Morning Briefing");
  });

  it("should prepend content to an existing file", async () => {
    const path = join(tmpDir, "prepend-existing.md");
    writeFileSync(path, "## Afternoon notes\n\nDid some work.\n");
    const job = makeJob({ output: path, prepend: true });
    await routeOutput("## Morning Briefing\n\n- item 1", job, tmpDir, { locksDir });
    const content = readFileSync(path, "utf-8");
    expect(content.indexOf("## Morning Briefing")).toBeLessThan(content.indexOf("## Afternoon notes"));
    expect(content).toContain("---");
  });

  it("should merge frontmatter when prepending", async () => {
    const path = join(tmpDir, "prepend-fm.md");
    writeFileSync(path, `---
date: 2026-06-15
type: daily-note
tags:
  - area/daily-notes
---

## Afternoon notes

Did some work.
`);
    const job = makeJob({ output: path, prepend: true });
    const newContent = `---
date: 2026-06-16
tags:
  - morning-briefing
---

## Morning Briefing

- item 1`;
    await routeOutput(newContent, job, tmpDir, { locksDir });
    const content = readFileSync(path, "utf-8");

    // Should have merged frontmatter arrays
    expect(content).toContain("area/daily-notes");
    expect(content).toContain("morning-briefing");
    // New content should come before existing
    expect(content.indexOf("## Morning Briefing")).toBeLessThan(content.indexOf("## Afternoon notes"));
    // Prepended frontmatter values should override existing scalars
    expect(content).toContain("date: 2026-06-16");
  });

  it("should substitute YYYY-MM-DD in paths", async () => {
    const today = new Date();
    const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
    const path = join(tmpDir, `daily-note-YYYY-MM-DD.md`);
    const job = makeJob({ output: join(tmpDir, "daily-note-YYYY-MM-DD.md") });
    const result = await routeOutput("test", job, tmpDir, { locksDir });
    expect(result).toContain(dateStr);
    expect(existsSync(join(tmpDir, `daily-note-${dateStr}.md`))).toBe(true);
  });

  it("should create parent directories", async () => {
    const path = join(tmpDir, "nested", "deep", "output.md");
    const job = makeJob({ output: path });
    await routeOutput("test", job, tmpDir, { locksDir });
    expect(existsSync(path)).toBe(true);
  });

  it("should return null when no output is set", async () => {
    const job = makeJob();
    const result = await routeOutput("test", job, tmpDir, { locksDir });
    expect(result).toBeNull();
  });

  it("writes via same-directory temp + atomic rename, leaving no temp files", async () => {
    const path = join(tmpDir, "atomic.md");
    await routeOutput("# hi", makeJob({ output: path }), tmpDir, { locksDir });
    expect(readFileSync(path, "utf-8")).toBe("# hi\n");
    expect(readdirSync(tmpDir).filter(f => f.endsWith(".tmp"))).toEqual([]);
  });

  it("throws and cleans up when the target is a directory", async () => {
    const dirPath = join(tmpDir, "as-directory.md");
    mkdirSync(dirPath);
    writeFileSync(join(dirPath, "keep.txt"), "x");
    await expect(
      routeOutput("text", makeJob({ output: dirPath }), tmpDir, { locksDir }),
    ).rejects.toThrow();
    // The directory is untouched and no temp file leaked.
    expect(readdirSync(dirPath)).toEqual(["keep.txt"]);
    // The output lock was released despite the failure.
    expect(readdirSync(locksDir)).toEqual([]);
  });

  it("throws when the output lock stays held by a live process", async () => {
    const path = join(tmpDir, "contended.md");
    // Prime the path so its lock key is stable, then hold the lock
    // in-process with a very short wait budget.
    await routeOutput("seed", makeJob({ output: path }), tmpDir, { locksDir });
    const lockKey = `output-${createHash("sha256").update(path).digest("hex").slice(0, 32)}`;
    acquireLock(lockKey, locksDir);
    try {
      await expect(
        routeOutput("blocked", makeJob({ output: path }), tmpDir, { locksDir, lockWaitMs: 300 }),
      ).rejects.toThrow("could not acquire output lock");
      // The held lock stopped the write.
      expect(readFileSync(path, "utf-8")).toBe("seed\n");
    } finally {
      releaseLock(lockKey, locksDir);
    }
  });
});

describe("output.ts multiprocess", () => {
  const tmpDir = join(tmpdir(), `cron-test-output-mp-${Date.now()}`);
  const locksDir = join(tmpDir, "locks");

  beforeAll(() => {
    mkdirSync(tmpDir, { recursive: true });
  });

  afterAll(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  it("concurrent prepend writers to one path all land", async () => {
    const path = join(tmpDir, "shared-note.md");
    const N = 6;
    // Distinct job names: the lock must key on the output path, not the job.
    const workers = Array.from({ length: N }, (_, i) =>
      startWorker(OUTPUT_WORKER, [`writer-${i}`, tmpDir, path, locksDir, "prepend"]));
    try {
      await Promise.all(workers.map(w => w.waitFor("ready")));
      for (const [i, w] of workers.entries()) w.send(`go:entry-${i}`);

      await Promise.all(workers.map(w => w.waitFor("done")));

      const content = readFileSync(path, "utf-8");
      for (let i = 0; i < N; i++) expect(content).toContain(`entry-${i}`);
      // No torn writes: exactly one intact line per writer.
      expect(content.match(/entry-\d+/g)).toHaveLength(N);
    } finally {
      for (const w of workers) w.kill();
    }
  }, 30_000);

  it("concurrent plain writers leave exactly one intact payload", async () => {
    const path = join(tmpDir, "overwrite-note.md");
    const N = 6;
    const workers = Array.from({ length: N }, (_, i) =>
      startWorker(OUTPUT_WORKER, [`overwriter-${i}`, tmpDir, path, locksDir, "write"]));
    try {
      await Promise.all(workers.map(w => w.waitFor("ready")));
      for (const [i, w] of workers.entries()) w.send(`go:payload-${i}||second-line-${i}`);

      await Promise.all(workers.map(w => w.waitFor("done")));

      // Atomic rename means the file is one writer's whole payload,
      // never an interleaving of two.
      expect(readFileSync(path, "utf-8")).toMatch(/^payload-\d\nsecond-line-\d\n$/);
    } finally {
      for (const w of workers) w.kill();
    }
  }, 30_000);
});
