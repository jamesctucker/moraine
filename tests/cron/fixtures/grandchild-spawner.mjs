// Spawns a SIGTERM-trapping grandchild that shares our stdout pipe,
// then exits — the grandchild alone keeps the pipe open, delaying the
// child's close event until the watchdog kills the process group.
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const trap = fileURLToPath(new URL("./sigterm-trap.mjs", import.meta.url));
const grand = spawn(process.execPath, [trap], {
  stdio: ["ignore", "inherit", "inherit"],
});
grand.unref();
process.stdout.write(`grand ${grand.pid}\n`);
