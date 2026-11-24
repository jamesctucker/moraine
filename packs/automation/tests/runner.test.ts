import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { isValid, matches } from "../runner/scheduler";
import { loadJobs, buildPrompt } from "../runner/job";
import { loadConfig } from "../runner/config";
import type { Job } from "../runner/types";
import { writeFileSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("runner integration", () => {
  const tmpDir = join(tmpdir(), `cron-test-runner-${Date.now()}`);

  beforeAll(() => {
    mkdirSync(tmpDir, { recursive: true });
  });

  afterAll(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  describe("--list", () => {
    it("should load jobs and display them", () => {
      writeFileSync(join(tmpDir, "job-1.yaml"), `
name: job-1
cron: "0 8 * * 1-5"
prompt: "morning prompt"
model: "custom-model"
output: "notes/daily-YYYY-MM-DD.md"
prepend: true
`);

      const jobs = loadJobs(tmpDir);
      expect(jobs).toHaveLength(1);
      expect(jobs[0].name).toBe("job-1");
      expect(jobs[0].prepend).toBe(true);
    });
  });

  const configDir = join(tmpDir, "config");

  describe("config resolution", () => {
    it("should merge config with defaults", () => {
      mkdirSync(configDir, { recursive: true });
      const configPath = join(configDir, "cron.config.yaml");
      writeFileSync(configPath, `
default:
  model: "my-model"
`);
      const config = loadConfig(configPath);
      expect(config.default.model).toBe("my-model");
      expect(config.default.timeout).toBe(600);
    });
  });

  describe("job model precedence", () => {
    it("job model > config default model", () => {
      mkdirSync(configDir, { recursive: true });
      writeFileSync(join(configDir, "cron.config.yaml"), `
default:
  model: "my-model"
`);
      writeFileSync(join(tmpDir, "model-job.yaml"), `
name: model-job
cron: "0 8 * * *"
prompt: "test"
model: "job-model"
`);

      const jobs = loadJobs(tmpDir);
      const config = loadConfig(join(configDir, "cron.config.yaml"));

      const jobModel = jobs.find((j: { name: string }) => j.name === "model-job")?.model;
      expect(jobModel).toBe("job-model"); // from job

      // For a job without model, config default should apply
      writeFileSync(join(tmpDir, "no-model-job.yaml"), `
name: no-model-job
cron: "0 9 * * *"
prompt: "test"
`);

      const jobs2 = loadJobs(tmpDir);
      const noModelJob = jobs2.find((j: { name: string }) => j.name === "no-model-job");
      expect(noModelJob?.model).toBeUndefined();
      expect(config.default.model).toBe("my-model"); // config supplies default
    });
  });

  describe("buildPrompt", () => {
    const baseJob: Job = {
      name: "test-job",
      cron: "0 8 * * *",
      prompt: "Do the thing.",
    };

    it("returns prompt unchanged when no skills", () => {
      expect(buildPrompt(baseJob)).toBe("Do the thing.");
    });

    it("returns prompt unchanged when skills is empty", () => {
      expect(buildPrompt({ ...baseJob, skills: [] })).toBe("Do the thing.");
    });

    it("prepends skill instruction for single skill", () => {
      const prompt = buildPrompt({ ...baseJob, skills: ["session-search"] });
      expect(prompt).toContain('Load the following skills using the skill tool: "session-search".');
      expect(prompt).toContain("Do the thing.");
      expect(prompt).toMatch(/^Load the following skills/);
    });

    it("prepends skill instruction for multiple skills", () => {
      const prompt = buildPrompt({
        ...baseJob,
        skills: ["session-search", "review-memory"],
      });
      expect(prompt).toContain('"session-search", "review-memory"');
      expect(prompt).toContain("Do the thing.");
    });
  });
});
