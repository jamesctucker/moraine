// Node (>= 23.6) can run the cron TypeScript modules directly, but they
// use bun-style extensionless relative imports. Loaded via
// `node --import`, this hook retries those specifiers with a .ts
// extension. Only used when bun is unavailable for test fixtures.
import { registerHooks } from "node:module";

const RELATIVE_WITHOUT_EXTENSION = /^\.{1,2}\//;

registerHooks({
  resolve(specifier, context, nextResolve) {
    try {
      return nextResolve(specifier, context);
    } catch (err) {
      if (RELATIVE_WITHOUT_EXTENSION.test(specifier) && !/\.[a-z]+$/i.test(specifier)) {
        return nextResolve(`${specifier}.ts`, context);
      }
      throw err;
    }
  },
});
