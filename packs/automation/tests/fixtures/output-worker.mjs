// Barrier-controlled output writer for the multiprocess output tests.
// Args: <jobName> <workspaceRoot> <outputPath> <locksDir> <mode>, where
// mode is "write" | "append" | "prepend". Line protocol: "go:<content>"
// on stdin ("||" stands in for a newline); "ready" and "done"/"error ..."
// on stdout.
import { createInterface } from "node:readline";
import { routeOutput } from "../../runner/output.ts";

const [jobName, workspaceRoot, outputPath, locksDir, mode] = process.argv.slice(2);

const rl = createInterface({ input: process.stdin });
rl.on("line", async (line) => {
  if (line === "exit") process.exit(0);
  if (!line.startsWith("go:")) return;
  const job = {
    name: jobName,
    cron: "* * * * *",
    prompt: "test",
    output: outputPath,
    append: mode === "append",
    prepend: mode === "prepend",
  };
  try {
    await routeOutput(line.slice(3).replaceAll("||", "\n"), job, workspaceRoot, { locksDir });
    console.log("done");
  } catch (e) {
    console.log(`error ${e.message}`);
  }
});
console.log("ready");

