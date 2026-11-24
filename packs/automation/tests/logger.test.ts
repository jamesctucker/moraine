import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { createLogger } from "../runner/logger";
import { existsSync, readFileSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import type { RunResult } from "../runner/types";

describe("logger.ts", () => {
  const logDir = join(tmpdir(), `cron-test-logs-${Date.now()}`);

  beforeAll(() => {
    mkdirSync(logDir, { recursive: true });
  });

  afterAll(() => {
    rmSync(logDir, { recursive: true, force: true });
  });

  it("should create a log file with correct format", () => {
    const logger = createLogger("test-job", logDir);
    const result: RunResult = {
      exitCode: 0,
      stdout: "Hello world\n",
      stderr: "",
      duration: 5,
    };
    const logPath = logger.writeLogFile(result, "test-model");

    expect(existsSync(logPath)).toBe(true);
    const content = readFileSync(logPath, "utf-8");
    expect(content).toContain("--- metadata ---");
    expect(content).toContain("job: test-job");
    expect(content).toContain("model: test-model");
    expect(content).toContain("exit_code: 0");
    expect(content).toContain("duration: 5s");
    expect(content).toContain("--- stdout ---");
    expect(content).toContain("Hello world");
    expect(content).toContain("--- stderr ---");
  });

  it("should log non-zero exit codes", () => {
    const logger = createLogger("failed-job", logDir);
    const result: RunResult = {
      exitCode: 1,
      stdout: "",
      stderr: "Error message",
      duration: 2,
    };
    const logPath = logger.writeLogFile(result, "test-model");
    const content = readFileSync(logPath, "utf-8");
    expect(content).toContain("exit_code: 1");
    expect(content).toContain("Error message");
  });
});
