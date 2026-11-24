import { spawn, spawnSync } from "node:child_process";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";

const TS_RESOLVE_HOOK = fileURLToPath(new URL("./fixtures/ts-resolve.mjs", import.meta.url));

let cachedCommand: string[] | null = null;

/**
 * The cron modules are TypeScript with bun-style extensionless imports,
 * so spawned fixtures run under bun when available. Node >= 23.6 is the
 * fallback (with a resolve hook that maps those imports to .ts files).
 */
export function fixtureRuntime(): string[] {
  if (cachedCommand === null) {
    const probe = spawnSync("bun", ["--version"], { stdio: "ignore" });
    cachedCommand = probe.status === 0
      ? ["bun"]
      : [process.execPath, "--import", TS_RESOLVE_HOOK];
  }
  return cachedCommand;
}

export interface FixtureWorker {
  pid: number;
  send(line: string): void;
  waitFor(prefix: string): Promise<string>;
  kill(): void;
}

/**
 * Spawns a barrier-controlled fixture worker speaking the line protocol:
 * commands on stdin, "ready" and result lines on stdout. The parent holds
 * every worker at "ready" and then releases them all at once.
 */
export function startWorker(scriptPath: string, args: string[]): FixtureWorker {
  const [command, ...prefixArgs] = fixtureRuntime();
  const child = spawn(command, [...prefixArgs, scriptPath, ...args], {
    stdio: ["pipe", "pipe", "pipe"],
  });
  const lines = createInterface({ input: child.stdout });
  const waiting: Array<{ prefix: string; resolve: (line: string) => void }> = [];
  lines.on("line", (line: string) => {
    const index = waiting.findIndex(w => line.startsWith(w.prefix));
    if (index !== -1) waiting.splice(index, 1)[0].resolve(line);
  });
  return {
    pid: child.pid!,
    send: (line: string) => child.stdin.write(`${line}\n`),
    waitFor: (prefix: string) =>
      new Promise<string>(resolve => waiting.push({ prefix, resolve })),
    kill: () => child.kill("SIGKILL"),
  };
}
