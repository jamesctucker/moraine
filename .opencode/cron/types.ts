export interface CronConfig {
  default: {
    model?: string;
    timeout: number;
  };
  log_dir: string;
  locks_dir: string;
  install_dir: string;
  work_models?: string[];
}

export interface EmailConfig {
  to: string;
  from?: string;
  /** Supports {date} (YYYY-MM-DD) and {name} (job name) tokens. */
  subject?: string;
}

export interface Job {
  name: string;
  cron: string;
  prompt: string;
  skills?: string[];
  model?: string;
  agent?: string;
  output?: string;
  append?: boolean;
  prepend?: boolean;
  timeout?: number;
  hostname?: string;
  disabled?: boolean;
  scope?: "work" | "personal";
  email?: EmailConfig;
}

export interface RunResult {
  exitCode: number;
  stdout: string;
  stderr: string;
  duration: number;
}
