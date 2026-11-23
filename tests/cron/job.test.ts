import { describe, it, expect, beforeAll, afterAll, beforeEach, vi } from "vitest";
import { loadJobs } from "../../.opencode/cron/job";
import { writeFileSync, mkdirSync, rmSync, readdirSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("job.ts", () => {
  const tmpDir = join(tmpdir(), `cron-test-jobs-${Date.now()}`);

  beforeAll(() => {
    mkdirSync(tmpDir, { recursive: true });
  });

  afterAll(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  beforeEach(() => {
    for (const entry of readdirSync(tmpDir)) {
      unlinkSync(join(tmpDir, entry));
    }
  });

  it("should load a valid job", () => {
    writeFileSync(join(tmpDir, "valid-job.yaml"), `
name: test-job
cron: "* * * * *"
prompt: "hello"
`);
    const jobs = loadJobs(tmpDir);
    expect(jobs).toHaveLength(1);
    expect(jobs[0].name).toBe("test-job");
    expect(jobs[0].cron).toBe("* * * * *");
  });

  it("should skip invalid YAML", () => {
    writeFileSync(join(tmpDir, "bad-yaml.yaml"), "::: not valid yaml :::");
    const jobs = loadJobs(tmpDir);
    expect(jobs.find(j => j.name === "bad-yaml")).toBeUndefined();
  });

  it("should skip files missing required fields", () => {
    writeFileSync(join(tmpDir, "missing-fields.yaml"), "name: foo\n");
    const jobs = loadJobs(tmpDir);
    expect(jobs.find(j => j.name === "foo")).toBeUndefined();
  });

  it("should reject append + prepend together", () => {
    writeFileSync(join(tmpDir, "bad-mode.yaml"), `
name: bad-mode
cron: "* * * * *"
prompt: "test"
append: true
prepend: true
output: "foo.md"
`);
    const jobs = loadJobs(tmpDir);
    expect(jobs.find(j => j.name === "bad-mode")).toBeUndefined();
  });

  it("should reject append/prepend without output", () => {
    writeFileSync(join(tmpDir, "missing-output.yaml"), `
name: missing-output
cron: "* * * * *"
prompt: "test"
prepend: true
`);
    const jobs = loadJobs(tmpDir);
    expect(jobs.find(j => j.name === "missing-output")).toBeUndefined();
  });

  it("should load optional fields", () => {
    writeFileSync(join(tmpDir, "full-job.yaml"), `
name: full-job
cron: "0 8 * * 1-5"
prompt: "do the thing"
model: "some-model"
agent: "some-agent"
output: "path/to/file.md"
prepend: true
timeout: 300
hostname: "myhost"
skills:
  - skill-a
  - skill-b
`);
    const jobs = loadJobs(tmpDir);
    expect(jobs).toHaveLength(1); // only full-job should load, previous files had errors
    const j = jobs[0];
    expect(j.model).toBe("some-model");
    expect(j.agent).toBe("some-agent");
    expect(j.output).toBe("path/to/file.md");
    expect(j.prepend).toBe(true);
    expect(j.timeout).toBe(300);
    expect(j.hostname).toBe("myhost");
    expect(j.skills).toEqual(["skill-a", "skill-b"]);
  });

  it("should skip jobs with invalid cron expressions", () => {
    writeFileSync(join(tmpDir, "bad-cron.yaml"), `
name: bad-cron
cron: "not a cron"
prompt: "test"
`);
    const jobs = loadJobs(tmpDir);
    expect(jobs.find(j => j.name === "bad-cron")).toBeUndefined();
  });

  it("should skip job names that are not bounded slugs", () => {
    // JSON is valid YAML and sidesteps quoting issues.
    const badNames = [
      "../evil",     // lock-path traversal
      "a/b",
      "a\\b",
      "bad name",
      "",
      "-leading",
      "semi;colon",
      "x".repeat(65), // one past the bound
    ];
    for (const name of badNames) {
      writeFileSync(join(tmpDir, "bad-name.yaml"), JSON.stringify({
        name, cron: "* * * * *", prompt: "test",
      }));
      expect(loadJobs(tmpDir).find(j => j.name === name)).toBeUndefined();
    }
  });

  it("should accept a 64-character slug name", () => {
    writeFileSync(join(tmpDir, "long-name.yaml"), JSON.stringify({
      name: "a".repeat(64), cron: "* * * * *", prompt: "test",
    }));
    const jobs = loadJobs(tmpDir);
    expect(jobs).toHaveLength(1);
    expect(jobs[0].name).toBe("a".repeat(64));
  });

  it("should reject unknown keys such as the removed scope gate", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    writeFileSync(join(tmpDir, "scoped-job.yaml"), `
name: scoped-job
cron: "* * * * *"
prompt: "test"
scope: work
`);

    const jobs = loadJobs(tmpDir);

    expect(jobs).toHaveLength(0);
    expect(warn.mock.calls.flat().join("\n")).toMatch(/scoped-job\.yaml.*scope/);
    warn.mockRestore();
  });

  it("should reject duplicate job names across files", () => {
    writeFileSync(join(tmpDir, "dup-a.yaml"), JSON.stringify({
      name: "dup", cron: "* * * * *", prompt: "first",
    }));
    writeFileSync(join(tmpDir, "dup-b.yaml"), JSON.stringify({
      name: "dup", cron: "* * * * *", prompt: "second",
    }));
    const jobs = loadJobs(tmpDir).filter(j => j.name === "dup");
    expect(jobs).toHaveLength(1);
    expect(jobs[0].prompt).toBe("first"); // entries sort: dup-a wins
  });

  it("should return empty array for non-existent directory", () => {
    const jobs = loadJobs("/nonexistent/path/12345");
    expect(jobs).toEqual([]);
  });
});
