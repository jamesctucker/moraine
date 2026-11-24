import { Cron } from "croner";

/**
 * The runner is fired once a minute from the system crontab, so
 * seconds-precision (6/7-field) expressions can never match — reject
 * them instead of accepting a schedule that silently never fires.
 */
function hasSubMinuteFields(expression: string): boolean {
  return expression.trim().split(/\s+/).length > 5;
}

export function isValid(expression: string): boolean {
  if (hasSubMinuteFields(expression)) return false;
  try {
    new Cron(expression);
    return true;
  } catch {
    return false;
  }
}

export function matches(expression: string, date?: Date): boolean {
  if (hasSubMinuteFields(expression)) return false;
  try {
    const now = date ?? new Date();
    const cron = new Cron(expression);

    // 5-field cron matches at second 0 only — round to the minute
    const minuteStart = new Date(now);
    minuteStart.setSeconds(0, 0);

    return cron.match(minuteStart);
  } catch {
    return false;
  }
}

export function getNextRun(expression: string, date?: Date): Date | null {
  if (hasSubMinuteFields(expression)) return null;
  try {
    const now = date ?? new Date();
    const cron = new Cron(expression);
    const next = cron.nextRun(now);
    return next ?? null;
  } catch {
    return null;
  }
}
