import { describe, it, expect } from "vitest";
import { buildMessage, expandSubject, renderHtml, sendJobEmail } from "../../.opencode/cron/email";
import { JobSchema } from "../../.opencode/cron/job";

const NOW = new Date(2026, 8, 7); // 2026-09-07 (a Monday)

describe("expandSubject", () => {
  it("expands {date} and {name} tokens", () => {
    expect(expandSubject("Recap — {date} ({name})", "weekly-recap", NOW))
      .toBe("Recap — 2026-09-07 (weekly-recap)");
  });

  it("defaults to a job/dated subject when no template given", () => {
    expect(expandSubject(undefined, "weekly-recap", NOW))
      .toBe("Garage cron — weekly-recap (2026-09-07)");
  });
});

describe("renderHtml", () => {
  it("renders markdown as HTML with a footer naming the job", () => {
    const html = renderHtml("# Title\n\n- one\n- two", "weekly-recap");
    expect(html).toContain("<h1>");
    expect(html).toContain("<li>one</li>");
    expect(html).toContain("job: weekly-recap");
  });
});

describe("buildMessage", () => {
  it("builds an RFC 822 message with headers + HTML body", () => {
    const msg = buildMessage(
      { to: "user@example.com", from: "OpenBench <recap@example.com>", subject: "Hi {date}" },
      "**bold**",
      "weekly-recap",
      NOW,
    );
    expect(msg).toContain("To: user@example.com");
    expect(msg).toContain("From: OpenBench <recap@example.com>");
    expect(msg).toContain("Subject: Hi 2026-09-07");
    expect(msg).toContain("Content-Type: text/html; charset=utf-8");
    expect(msg).toContain("<strong>bold</strong>");
  });

  it("falls back to a default From when omitted", () => {
    const msg = buildMessage({ to: "user@example.com" }, "hi", "some-job", NOW);
    expect(msg).toContain("From: Garage Cron <garage-cron@localhost>");
  });
});

describe("sendJobEmail", () => {
  it("hands the full message to the mailer (never shells out in tests)", () => {
    let captured = "";
    sendJobEmail(
      { to: "user@example.com" },
      "weekly-recap",
      "# Recap",
      NOW,
      (message) => { captured = message; },
    );
    expect(captured).toContain("To: user@example.com");
    expect(captured).toContain("<h1>");
  });
});

describe("JobSchema", () => {
  it("accepts a job with an email block", () => {
    const result = JobSchema.safeParse({
      name: "weekly-recap",
      cron: "0 8 * * 1",
      prompt: "do things",
      email: { to: "user@example.com", subject: "Recap — {date}" },
    });
    expect(result.success).toBe(true);
  });

  it("rejects email without a recipient", () => {
    const result = JobSchema.safeParse({
      name: "bad",
      cron: "0 8 * * 1",
      prompt: "do things",
      email: { subject: "no to" },
    });
    expect(result.success).toBe(false);
  });
});
