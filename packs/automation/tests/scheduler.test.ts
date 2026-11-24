import { describe, it, expect } from "vitest";
import { isValid, matches, getNextRun } from "../runner/scheduler";

describe("scheduler.ts", () => {
  describe("isValid", () => {
    it("should accept standard 5-field cron", () => {
      expect(isValid("* * * * *")).toBe(true);
      expect(isValid("0 8 * * 1-5")).toBe(true);
      expect(isValid("0 9 * * 1")).toBe(true);
      expect(isValid("*/5 * * * *")).toBe(true);
      expect(isValid("0 0 1 1 *")).toBe(true);
    });

    it("should reject invalid expressions", () => {
      expect(isValid("not a cron")).toBe(false);
      expect(isValid("")).toBe(false);
      expect(isValid("* * *")).toBe(false);
      expect(isValid("99 * * * *")).toBe(false);
    });

    it("should reject seconds-based (6-field) expressions", () => {
      // Croner accepts these, but the runner only fires once a minute,
      // so they could never match.
      expect(isValid("30 * * * * *")).toBe(false);
      expect(isValid("*/10 * * * * *")).toBe(false);
      expect(isValid("0 30 8 * * *")).toBe(false);
    });

    it("should reject 7-field expressions", () => {
      expect(isValid("0 0 0 1 1 * 2027")).toBe(false);
    });
  });

  describe("matches", () => {
    it("should match when the minute lines up", () => {
      // June 15, 2026 08:00 local is a Monday
      const monday = new Date(2026, 5, 15, 8, 0, 0);
      expect(matches("0 8 * * 1", monday)).toBe(true);
    });

    it("should not match when the day-of-week differs", () => {
      // June 16, 2026 08:00 local is a Tuesday
      const tuesday = new Date(2026, 5, 16, 8, 0, 0);
      expect(matches("0 8 * * 1", tuesday)).toBe(false);
    });

    it("should not match when the hour differs", () => {
      const monday = new Date(2026, 5, 15, 9, 0, 0);
      expect(matches("0 8 * * 1", monday)).toBe(false);
    });

    it("should match every minute for * * * * *", () => {
      const now = new Date();
      expect(matches("* * * * *", now)).toBe(true);
    });

    it("should handle */5 intervals", () => {
      const at5 = new Date(2026, 5, 15, 8, 5, 0);
      const at3 = new Date(2026, 5, 15, 8, 3, 0);
      expect(matches("*/5 * * * *", at5)).toBe(true);
      expect(matches("*/5 * * * *", at3)).toBe(false);
    });

    it("should refuse sub-minute expressions", () => {
      expect(matches("30 * * * * *", new Date())).toBe(false);
    });
  });

  describe("getNextRun", () => {
    it("should return a date in the future", () => {
      const before = new Date(2026, 5, 15, 7, 59, 0); // 7:59 Monday
      const next = getNextRun("0 8 * * 1", before);
      expect(next).not.toBeNull();
      expect(next!.getHours()).toBe(8);
      expect(next!.getMinutes()).toBe(0);
    });

    it("should return null for invalid expressions", () => {
      expect(getNextRun("invalid")).toBeNull();
    });

    it("should return null for sub-minute expressions", () => {
      expect(getNextRun("30 * * * * *")).toBeNull();
    });
  });
});
