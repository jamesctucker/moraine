import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CronConfig, Job } from "../../.opencode/cron/types";

const mocks = vi.hoisted(() => ({
  routeOutput: vi.fn(),
  runWithTimeout: vi.fn(),
  acquireLock: vi.fn(),
  releaseLock: vi.fn(),
  writeLogFile: vi.fn(),
  writeToConsole: vi.fn(),
  sendJobEmail: vi.fn(),
}));

vi.mock("../../.opencode/cron/output", () => ({ routeOutput: mocks.routeOutput }));
vi.mock("../../.opencode/cron/spawn", () => ({ runWithTimeout: mocks.runWithTimeout }));
vi.mock("../../.opencode/cron/lock", async (importOriginal) => ({
  ...(await importOriginal()),
  acquireLock: mocks.acquireLock,
  releaseLock: mocks.releaseLock,
}));
vi.mock("../../.opencode/cron/logger", () => ({
  createLogger: () => ({
    writeLogFile: mocks.writeLogFile,
    writeToConsole: mocks.writeToConsole,
  }),
}));
vi.mock("../../.opencode/cron/email", () => ({ sendJobEmail: mocks.sendJobEmail }));

import { runJob } from "../../.opencode/cron/runner";

const job: Job = {
  name: "output-job",
  cron: "0 8 * * *",
  prompt: "work",
  output: "notes/daily.md",
  email: { to: "james@example.com" },
};
const config: CronConfig = {
  default: { timeout: 10 },
  log_dir: "/tmp/logs",
  locks_dir: "/tmp/locks",
  install_dir: "/tmp/jobs",
};

describe("runJob output failures", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.acquireLock.mockReturnValue(true);
    mocks.writeLogFile.mockReturnValue("/tmp/logs/output-job.log");
    mocks.runWithTimeout.mockResolvedValue({
      exitCode: 0,
      stdout: "completed output",
      stderr: "",
      duration: 1,
      timedOut: false,
    });
  });

  it("logs the run and returns a job failure without sending success email", async () => {
    mocks.routeOutput.mockRejectedValue(new Error("output lock timed out"));

    await expect(runJob(job, config, false)).resolves.toBe(1);

    expect(mocks.writeLogFile).toHaveBeenCalledWith(
      expect.objectContaining({
        exitCode: 1,
        stdout: "completed output",
        stderr: expect.stringContaining("output lock timed out"),
      }),
      "",
    );
    expect(mocks.writeToConsole).toHaveBeenCalledWith("FAILED", ["completed output"]);
    expect(mocks.sendJobEmail).not.toHaveBeenCalled();
    expect(mocks.releaseLock).toHaveBeenCalledWith("output-job", "/tmp/locks");
  });

  it("keeps the successful output path intact", async () => {
    mocks.routeOutput.mockResolvedValue("notes/daily.md");

    await expect(runJob(job, config, false)).resolves.toBe(0);

    expect(mocks.writeToConsole).toHaveBeenCalledWith("OK", ["completed output"]);
    expect(mocks.sendJobEmail).toHaveBeenCalledOnce();
    expect(mocks.releaseLock).toHaveBeenCalledOnce();
  });
});
