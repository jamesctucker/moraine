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
      { to: "user@example.com", from: "Moraine <recap@example.com>", subject: "Hi {date}" },
      "**bold**",
      "weekly-recap",
      NOW,
    );
    expect(msg).toContain("To: user@example.com");
    expect(msg).toContain("From: Moraine <recap@example.com>");
    expect(msg).toContain("Subject: Hi 2026-09-07");
    expect(msg).toContain("Content-Type: text/html; charset=utf-8");
    expect(msg).toContain("<strong>bold</strong>");
  });

  it("falls back to a default From when omitted", () => {
    const msg = buildMessage({ to: "user@example.com" }, "hi", "some-job", NOW);
    expect(msg).toContain("From: Moraine Cron <moraine-cron@localhost>");
  });

  it("accepts a comma-separated recipient list", () => {
    const msg = buildMessage(
      { to: "a@example.com, Display Name <b@example.com>" },
      "hi",
      "some-job",
      NOW,
    );
    expect(msg).toContain("To: a@example.com, Display Name <b@example.com>");
  });

  it("rejects a Bcc injection in To", () => {
    expect(() =>
      buildMessage({ to: "user@example.com\r\nBcc: attacker@evil.example" }, "hi", "job", NOW),
    ).toThrow(/email\.to/);
    expect(() =>
      buildMessage({ to: "user@example.com\nBcc: attacker@evil.example" }, "hi", "job", NOW),
    ).toThrow(/email\.to/);
  });

  it("rejects CR/LF in From", () => {
    expect(() =>
      buildMessage(
        { to: "user@example.com", from: "x@example.com\r\nBcc: attacker@evil.example" },
        "hi",
        "job",
        NOW,
      ),
    ).toThrow(/email\.from/);
  });

  it("rejects CR/LF in the expanded subject", () => {
    expect(() =>
      buildMessage(
        { to: "user@example.com", subject: "Weekly\nBcc: attacker@evil.example" },
        "hi",
        "job",
        NOW,
      ),
    ).toThrow(/email\.subject/);
  });

  it("rejects malformed addresses", () => {
    expect(() => buildMessage({ to: "not an address" }, "hi", "job", NOW)).toThrow(/email\.to/);
    expect(() => buildMessage({ to: "user@" }, "hi", "job", NOW)).toThrow(/email\.to/);
    expect(() => buildMessage({ to: "user@example.com," }, "hi", "job", NOW)).toThrow(/email\.to/);
    expect(() =>
      buildMessage({ to: "user@example.com", from: "<>" }, "hi", "job", NOW),
    ).toThrow(/email\.from/);
  });
});

describe("renderHtml escaping", () => {
  it("escapes HTML in the job name footer", () => {
    const html = renderHtml("# Title", `<script>alert("x")</script>`);
    expect(html).toContain("job: &lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;");
    expect(html).not.toContain("<script>");
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

  it("rejects a Bcc injection in any email field", () => {
    const injections = [
      { email: { to: "user@example.com\r\nBcc: attacker@evil.example" } },
      { email: { to: "user@example.com", from: "x@y.example\nBcc: attacker@evil.example" } },
      { email: { to: "user@example.com", subject: "s\r\nBcc: attacker@evil.example" } },
    ];
    for (const email of injections) {
      const result = JobSchema.safeParse({
        name: "evil-job",
        cron: "0 8 * * 1",
        prompt: "do things",
        ...email,
      });
      expect(result.success).toBe(false);
    }
  });

  it("rejects malformed recipient addresses", () => {
    const result = JobSchema.safeParse({
      name: "evil-job",
      cron: "0 8 * * 1",
      prompt: "do things",
      email: { to: "not an address" },
    });
    expect(result.success).toBe(false);
  });

  it("accepts a display-name recipient and a comma-separated list", () => {
    const result = JobSchema.safeParse({
      name: "weekly-recap",
      cron: "0 8 * * 1",
      prompt: "do things",
      email: { to: "Moraine <recap@example.com>, user@example.com" },
    });
    expect(result.success).toBe(true);
  });
});
