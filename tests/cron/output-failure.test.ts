import { describe, it, expect, beforeAll, afterAll, vi } from "vitest";
import { mkdirSync, rmSync, readdirSync, writeFileSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

// Inject a rename failure at the final atomic step of routeOutput —
// after the temp file is written, before the destination is replaced.
const { renameSync } = vi.hoisted(() => ({
  renameSync: vi.fn(() => {
    throw Object.assign(new Error("injected rename failure"), { code: "EIO" });
  }),
}));

vi.mock("node:fs", async (importOriginal) => {
  const actual = await importOriginal<typeof import("node:fs")>();
  return { ...actual, renameSync };
});

import { routeOutput } from "../../.opencode/cron/output";
import type { Job } from "../../.opencode/cron/types";

describe("output.ts injected write failure", () => {
  const tmpDir = join(tmpdir(), `cron-test-output-fail-${Date.now()}`);
  const locksDir = join(tmpDir, "locks");

  beforeAll(() => {
    mkdirSync(tmpDir, { recursive: true });
  });

  afterAll(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  it("keeps the existing file intact and releases the lock", async () => {
    const path = join(tmpDir, "preserve.md");
    writeFileSync(path, "original content\n");
    const job: Job = {
      name: "failing-job",
      cron: "* * * * *",
      prompt: "test",
      output: path,
      prepend: true,
    };

    await expect(routeOutput("new content", job, tmpDir, { locksDir })).rejects.toThrow(
      "injected rename failure",
    );

    // The read-modify-write never reached the destination.
    expect(readFileSync(path, "utf-8")).toBe("original content\n");
    // The temp file was cleaned up.
    expect(readdirSync(tmpDir).filter(f => f.endsWith(".tmp"))).toEqual([]);
    // The output lock was released despite the failure.
    expect(readdirSync(locksDir)).toEqual([]);
    expect(renameSync).toHaveBeenCalled();
  });
});
