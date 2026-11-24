import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { loadConfig } from "../runner/config";
import { writeFileSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("config.ts", () => {
  const tmpDir = join(tmpdir(), `cron-test-config-${Date.now()}`);

  beforeAll(() => {
    mkdirSync(tmpDir, { recursive: true });
  });

  afterAll(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  it("should return defaults when config file is missing", () => {
    const config = loadConfig(join(tmpDir, "nonexistent.yaml"));
    expect(config.default.timeout).toBe(600);
    expect(config.log_dir).toBe("packs/automation/.logs");
    expect(config.locks_dir).toBe("~/.moraine/cron/.locks");
    expect(config.install_dir).toBe("~/.moraine/cron");
  });

  it("should keep Moraine defaults when config is invalid", () => {
    const configPath = join(tmpDir, "invalid-schema.yaml");
    writeFileSync(configPath, "default: 3\n"); // wrong type → schema failure
    const config = loadConfig(configPath);
    expect(config.locks_dir).toBe("~/.moraine/cron/.locks");
    expect(config.install_dir).toBe("~/.moraine/cron");
  });

  it("should load a valid config file", () => {
    const configPath = join(tmpDir, "valid-config.yaml");
    writeFileSync(configPath, `
default:
  model: "test-model"
  timeout: 300
log_dir: "custom/logs"
locks_dir: "custom/locks"
install_dir: "custom/cron"
`);
    const config = loadConfig(configPath);
    expect(config.default.model).toBe("test-model");
    expect(config.default.timeout).toBe(300);
    expect(config.log_dir).toBe("custom/logs");
    expect(config.locks_dir).toBe("custom/locks");
    expect(config.install_dir).toBe("custom/cron");
  });

  it("should merge partial config with defaults", () => {
    const configPath = join(tmpDir, "partial-config.yaml");
    writeFileSync(configPath, `
default:
  model: "partial-model"
`);
    const config = loadConfig(configPath);
    expect(config.default.model).toBe("partial-model");
    expect(config.default.timeout).toBe(600); // built-in default
  });

  it("should handle invalid YAML gracefully", () => {
    const configPath = join(tmpDir, "bad-config.yaml");
    writeFileSync(configPath, ":::invalid:::");
    const config = loadConfig(configPath);
    expect(config.default.timeout).toBe(600); // falls back to defaults
  });
});
