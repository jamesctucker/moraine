import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import type { RunResult } from "./types";

export interface Logger {
  writeToConsole(status: string, previewLines?: string[]): void;
  writeLogFile(result: RunResult, model: string): string;
}

export function createLogger(jobName: string, logDir: string): Logger {
  const now = new Date();
  const timestamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}_${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(2, "0")}${String(now.getSeconds()).padStart(2, "0")}`;
  const logFileName = `${timestamp}_${jobName}.log`;

  return {
    writeToConsole(status: "OK" | "FAILED", previewLines: string[] = []) {
      console.log(`  [${jobName}] ${status}`);
      for (const line of previewLines.slice(0, 5)) {
        console.log(`    ${line.length > 120 ? line.slice(0, 120) + "..." : line}`);
      }
    },

    writeLogFile(result: RunResult, model: string): string {
      mkdirSync(logDir, { recursive: true });
      const logPath = join(logDir, logFileName);

      const lines = [
        "--- metadata ---",
        `job: ${jobName}`,
        `model: ${model}`,
        `started: ${now.toISOString()}`,
        `duration: ${result.duration}s`,
        `exit_code: ${result.exitCode}`,
        "",
        "--- stdout ---",
        result.stdout,
        "",
        "--- stderr ---",
        result.stderr,
      ];

      writeFileSync(logPath, lines.join("\n"), "utf-8");
      return logPath;
    },
  };
}
