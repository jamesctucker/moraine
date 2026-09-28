import { readFileSync } from "node:fs";
import { parse } from "yaml";
import { z } from "zod";
import type { CronConfig } from "./types";

const CronConfigSchema = z.object({
  default: z.object({
    model: z.string().optional(),
    timeout: z.number().default(600),
  }).default({ timeout: 600 }),
  log_dir: z.string().default("scheduled/.logs"),
  locks_dir: z.string().default("~/.garage/cron/.locks"),
  install_dir: z.string().default("~/.garage/cron"),
  work_models: z.array(z.string()).optional(),
});

export function loadConfig(configPath: string): CronConfig {
  try {
    const raw = readFileSync(configPath, "utf-8");
    const parsed = parse(raw);
    const result = CronConfigSchema.safeParse(parsed);
    if (result.success) {
      return result.data as CronConfig;
    }
    console.warn(`Warning: invalid cron config: ${result.error.message}, using defaults`);
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code !== "ENOENT") {
      console.warn(`Warning: could not read cron config: ${(e as Error).message}, using defaults`);
    }
  }
  return CronConfigSchema.parse({}) as CronConfig;
}
