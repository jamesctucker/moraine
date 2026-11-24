import { describe, it, expect } from "vitest";

describe("vitest infrastructure", () => {
  it("should run a basic test", () => {
    expect(1 + 1).toBe(2);
  });

  it("should handle strings", () => {
    expect("hello".toUpperCase()).toBe("HELLO");
  });
});
