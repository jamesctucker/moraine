// Barrier-controlled lock worker for the multiprocess lock tests.
// Line protocol: "acquire"/"release"/"exit" on stdin; "ready",
// "acquired <bool>" and "released" on stdout.
import { createInterface } from "node:readline";
import { acquireLock, releaseLock } from "../../runner/lock.ts";

const [jobName, locksDir] = process.argv.slice(2);

const rl = createInterface({ input: process.stdin });
rl.on("line", (line) => {
  if (line === "acquire") {
    console.log(`acquired ${acquireLock(jobName, locksDir)}`);
  } else if (line === "release") {
    releaseLock(jobName, locksDir);
    console.log("released");
  } else if (line === "exit") {
    process.exit(0);
  }
});
console.log("ready");
