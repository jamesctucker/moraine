import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

// Vitest for the automation pack. Root is this pack's folder, so `tests/**`
// resolves to packs/automation/tests no matter where vitest is invoked from.
export default defineConfig({
  test: {
    root: fileURLToPath(new URL(".", import.meta.url)),
    include: ["tests/**/*.test.ts", "tests/**/*.test.mjs", "tests/**/*.spec.ts"],
    watch: false,
  },
});
