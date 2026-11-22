import { readdirSync, readFileSync } from "node:fs";
import { join, extname } from "node:path";
import { parse } from "yaml";
import { z } from "zod";
import { isValid } from "./scheduler";
import { LOCK_KEY_PATTERN } from "./lock";
import { recipientError, recipientsError, subjectError } from "./email";
import type { CronConfig, Job } from "./types";

export const JobSchema = z.object({
  name: z.string().regex(LOCK_KEY_PATTERN, {
    message: "must be a slug: letters, digits, '_' or '-', at most 64 chars, no separators",
  }),
  cron: z.string(),
  prompt: z.string(),
  skills: z.array(z.string()).optional(),
  model: z.string().optional(),
  agent: z.string().optional(),
  output: z.string().optional(),
  append: z.boolean().optional(),
  prepend: z.boolean().optional(),
  timeout: z.number().optional(),
  hostname: z.string().optional(),
  disabled: z.boolean().optional(),
  scope: z.enum(["work", "personal"]).optional(),
  email: z.object({
    to: z.string().refine(v => recipientsError(v) === null, {
      message: "must be valid address(es) — 'user@host' or 'Name <user@host>', comma-separated, no CR/LF",
    }),
    from: z.string().refine(v => recipientError(v) === null, {
      message: "must be a valid address — 'user@host' or 'Name <user@host>', no CR/LF",
    }).optional(),
    subject: z.string().refine(v => subjectError(v) === null, {
      message: "must not contain CR/LF",
    }).optional(),
  }).optional(),
});

/**
 * Work-model gate: jobs marked scope:work must run on a model in the
 * OpenRouter allowlist (config.work_models). Returns a one-line violation
 * message, or null when the job is allowed (or not work-scoped).
 */
export function workScopeViolation(job: Job, config: CronConfig): string | null {
  if (job.scope !== "work") return null;
  if (job.agent) {
    return `job '${job.name}' is scope:work but sets 'agent' — scope:work jobs cannot use a custom agent (unvalidated model) — set model directly`;
  }
  const effectiveModel = job.model ?? config.default?.model;
  const allowlist = config.work_models ?? [];
  if (!effectiveModel || !allowlist.includes(effectiveModel)) {
    return `job '${job.name}' is scope:work but its effective model '${effectiveModel ?? "(none)"}' is not in the OpenRouter work_models allowlist [${allowlist.join(", ") || "(empty)"}]`;
  }
  return null;
}

export function buildPrompt(job: Job): string {
  if (!job.skills?.length) return job.prompt;
  const skills = job.skills.map(s => `"${s}"`).join(", ");
  return `Load the following skills using the skill tool: ${skills}.\n\n${job.prompt}`;
}

export function loadJobs(directory: string): Job[] {
  const jobs: Job[] = [];
  const seenNames = new Set<string>();
  let entries: string[];

  try {
    entries = readdirSync(directory);
  } catch {
    return jobs;
  }

  for (const entry of entries.sort()) {
    const ext = extname(entry).toLowerCase();
    if (ext !== ".yaml" && ext !== ".yml") continue;

    const filePath = join(directory, entry);
    try {
      const raw = readFileSync(filePath, "utf-8");
      const parsed = parse(raw);
      if (typeof parsed !== "object" || parsed === null) {
        console.warn(`Warning: skipping ${entry}: not a valid YAML object`);
        continue;
      }

      const result = JobSchema.safeParse(parsed);
      if (!result.success) {
        console.warn(`Warning: skipping ${entry}: ${result.error.issues.map(i => `${i.path.join(".")}: ${i.message}`).join(", ")}`);
        continue;
      }

      const job = result.data as Job;

      if (job.append && job.prepend) {
        console.warn(`Warning: skipping ${entry}: cannot set both 'append' and 'prepend'`);
        continue;
      }

      if ((job.append || job.prepend) && !job.output) {
        console.warn(`Warning: skipping ${entry}: 'output' is required when 'append' or 'prepend' is true`);
        continue;
      }

      if (!isValid(job.cron)) {
        console.warn(`Warning: skipping ${entry}: invalid cron expression '${job.cron}'`);
        continue;
      }

      if (seenNames.has(job.name)) {
        console.warn(`Warning: skipping ${entry}: duplicate job name '${job.name}' (already defined by another file)`);
        continue;
      }
      seenNames.add(job.name);

      jobs.push(job);
    } catch (e) {
      console.warn(`Warning: skipping ${entry}: ${(e as Error).message}`);
    }
  }

  return jobs;
}
