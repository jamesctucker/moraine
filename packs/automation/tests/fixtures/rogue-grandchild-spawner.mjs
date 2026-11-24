// Like grandchild-spawner, but the grandchild is spawned detached into
// its own process group: the watchdog's group kill cannot reach it, so
// the runner must settle via its final settle deadline instead of the
// close event.
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const trap = fileURLToPath(new URL("./sigterm-trap.mjs", import.meta.url));
const grand = spawn(process.execPath, [trap], {
  stdio: ["ignore", "inherit", "inherit"],
  detached: true,
});
grand.unref();
process.stdout.write(`grand ${grand.pid}\n`);
