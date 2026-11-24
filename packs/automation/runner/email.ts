import { execFileSync } from "node:child_process";
import { marked } from "marked";
import type { EmailConfig } from "./types";

const DEFAULT_FROM = "Moraine Cron <moraine-cron@localhost>";

/** Injectable so tests never touch msmtp. Takes a full RFC 822 message. */
export type Mailer = (message: string) => void;

const CRLF = /[\r\n]/;
const ADDR_SPEC = /^[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*$/;

/**
 * Validates one address value: `user@host` or `Display Name <user@host>`.
 * Returns null when valid, else a short reason. Every value that becomes
 * a header must pass through here or subjectError — msmtp runs with -t,
 * so a CR/LF in any field can inject an extra header such as Bcc.
 */
export function recipientError(raw: string): string | null {
  if (CRLF.test(raw)) return "must not contain CR/LF";
  const trimmed = raw.trim();
  const named = trimmed.match(/^([^<>]*)<([^<>]*)>$/);
  const addr = named ? named[2].trim() : trimmed;
  if (!ADDR_SPEC.test(addr)) return `is not a valid address: '${addr}'`;
  return null;
}

/** Validates a comma-separated recipient list for the To: header. */
export function recipientsError(raw: string): string | null {
  if (CRLF.test(raw)) return "must not contain CR/LF";
  const list = raw.split(",").map(s => s.trim());
  if (list.some(s => !s)) return "must not contain empty recipients";
  for (const entry of list) {
    const err = recipientError(entry);
    if (err) return err;
  }
  return null;
}

/** The subject is free text but must stay a single header line. */
export function subjectError(raw: string): string | null {
  if (CRLF.test(raw)) return "must not contain CR/LF";
  return null;
}

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

function escapeHtml(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function renderHtml(markdown: string, jobName: string): string {
  const body = marked.parse(markdown, { async: false }) as string;
  return [
    "<!DOCTYPE html>",
    '<html><head><meta charset="utf-8"></head>',
    '<body style="font-family: -apple-system, sans-serif; max-width: 720px; margin: 0 auto; padding: 16px;">',
    body,
    '<hr style="border: none; border-top: 1px solid #ddd; margin-top: 24px;">',
    `<p style="color: #888; font-size: 12px;">Sent by Moraine Cron (job: ${escapeHtml(jobName)})</p>`,
    "</body></html>",
  ].join("\n");
}

export function buildMessage(
  email: EmailConfig,
  markdown: string,
  jobName: string,
  now: Date = new Date(),
): string {
  const toError = recipientsError(email.to);
  if (toError) throw new Error(`email.to ${toError}`);
  if (email.from !== undefined) {
    const fromError = recipientError(email.from);
    if (fromError) throw new Error(`email.from ${fromError}`);
  }
  const subject = expandSubject(email.subject, jobName, now);
  const subjError = subjectError(subject);
  if (subjError) throw new Error(`email.subject ${subjError}`);

  const headers = [
    `To: ${email.to}`,
    `From: ${email.from ?? DEFAULT_FROM}`,
    `Subject: ${subject}`,
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
