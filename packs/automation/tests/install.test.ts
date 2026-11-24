import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { installEnabled, readEnabledJobs } from "../runner/install";
import { existsSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("install.ts", () => {
  const tmpDir = join(tmpdir(), `cron-test-install-${Date.now()}`);
  // A fake workspace: enabled.json entries are resolved against its root,
  // and shipped jobs are discovered under its packs/*/jobs/.
  const workspaceRoot = join(tmpDir, "workspace");
  const targetDir = join(tmpDir, "target");
  const enabledFile = join(targetDir, "enabled.json");

  beforeAll(() => {
    mkdirSync(join(workspaceRoot, "packs", "demo", "jobs"), { recursive: true });
    mkdirSync(join(workspaceRoot, "packs", "local", "jobs"), { recursive: true });
    writeFileSync(join(workspaceRoot, "packs", "demo", "jobs", "job-a.yaml"), "name: a\ncron: '* * * * *'\nprompt: test\n");
    writeFileSync(join(workspaceRoot, "packs", "local", "jobs", "job-b.yml"), "name: b\ncron: '* * * * *'\nprompt: test\n");
  });

  afterAll(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  it("should copy the enabled jobs, resolved against the workspace root", () => {
    mkdirSync(targetDir, { recursive: true });
    writeFileSync(enabledFile, JSON.stringify({
      jobs: ["packs/demo/jobs/job-a.yaml", "packs/local/jobs/job-b.yml"],
    }));

    const count = installEnabled(enabledFile, targetDir, workspaceRoot);
    expect(count).toBe(2);
    expect(existsSync(join(targetDir, "job-a.yaml"))).toBe(true);
    expect(existsSync(join(targetDir, "job-b.yml"))).toBe(true);
  });

  it("should remove installed job files that are shipped but no longer enabled", () => {
    writeFileSync(enabledFile, JSON.stringify({ jobs: ["packs/demo/jobs/job-a.yaml"] }));

    const count = installEnabled(enabledFile, targetDir, workspaceRoot);
    expect(count).toBe(1);
    expect(existsSync(join(targetDir, "job-a.yaml"))).toBe(true);
    expect(existsSync(join(targetDir, "job-b.yml"))).toBe(false);
  });

  it("should keep installed files that match no shipped job", () => {
    writeFileSync(join(targetDir, "my-own-job.yaml"), "name: mine\ncron: '* * * * *'\nprompt: test\n");

    installEnabled(enabledFile, targetDir, workspaceRoot);
    expect(existsSync(join(targetDir, "my-own-job.yaml"))).toBe(true);
  });

  it("should report missing enabled jobs instead of failing", () => {
    writeFileSync(enabledFile, JSON.stringify({ jobs: ["packs/demo/jobs/gone.yaml"] }));

    const count = installEnabled(enabledFile, targetDir, workspaceRoot);
    expect(count).toBe(0);
    expect(existsSync(join(targetDir, "gone.yaml"))).toBe(false);
  });

  it("should read an empty list when enabled.json is missing or invalid", () => {
    expect(readEnabledJobs(join(tmpDir, "nonexistent.json"))).toEqual([]);

    const invalid = join(tmpDir, "invalid.json");
    writeFileSync(invalid, "not json");
    expect(readEnabledJobs(invalid)).toEqual([]);

    const wrongShape = join(tmpDir, "wrong-shape.json");
    writeFileSync(wrongShape, JSON.stringify({ jobs: "not-a-list" }));
    expect(readEnabledJobs(wrongShape)).toEqual([]);
  });
});
