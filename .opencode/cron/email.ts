import { execFileSync } from "node:child_process";
import { marked } from "marked";
import type { EmailConfig } from "./types";

const DEFAULT_FROM = "Garage Cron <garage-cron@localhost>";

/** Injectable so tests never touch msmtp. Takes a full RFC 822 message. */
export type Mailer = (message: string) => void;

/**
 * Sends a job's final stdout as an HTML email via msmtp (default account,
 * which owns SMTP auth and envelope-from per ~/.msmtprc).
 */
const defaultMailer: Mailer = (message) => {
  execFileSync("msmtp", ["-a", "default", "-t"], {
    input: message,
    stdio: ["pipe", "pipe", "pipe"],
  });
};

function todayIso(now: Date): string {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export function expandSubject(template: string | undefined, jobName: string, now: Date): string {
  return (template ?? `Garage cron — {name} ({date})`)
    .replaceAll("{date}", todayIso(now))
    .replaceAll("{name}", jobName);
}

export function renderHtml(markdown: string, jobName: string): string {
  const body = marked.parse(markdown, { async: false }) as string;
  return [
    "<!DOCTYPE html>",
    '<html><head><meta charset="utf-8"></head>',
    '<body style="font-family: -apple-system, sans-serif; max-width: 720px; margin: 0 auto; padding: 16px;">',
    body,
    '<hr style="border: none; border-top: 1px solid #ddd; margin-top: 24px;">',
    `<p style="color: #888; font-size: 12px;">Sent by Garage Cron (job: ${jobName})</p>`,
    "</body></html>",
  ].join("\n");
}

export function buildMessage(
  email: EmailConfig,
  markdown: string,
  jobName: string,
  now: Date = new Date(),
): string {
  const headers = [
    `To: ${email.to}`,
    `From: ${email.from ?? DEFAULT_FROM}`,
    `Subject: ${expandSubject(email.subject, jobName, now)}`,
    "MIME-Version: 1.0",
    "Content-Type: text/html; charset=utf-8",
  ];
  return `${headers.join("\r\n")}\r\n\r\n${renderHtml(markdown, jobName)}`;
}

/**
 * Sends the job output as an email. Throws on msmtp failure/missing binary —
 * callers should catch so email never fails the job itself.
 */
export function sendJobEmail(
  email: EmailConfig,
  jobName: string,
  markdown: string,
  now: Date = new Date(),
  mailer: Mailer = defaultMailer,
): void {
  mailer(buildMessage(email, markdown, jobName, now));
}
