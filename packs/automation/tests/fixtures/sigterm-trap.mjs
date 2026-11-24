// Traps SIGTERM and keeps running — only SIGKILL can remove it.
// Prints "pid <n>" so tests can verify the process is really gone.
process.on("SIGTERM", () => {
  process.stdout.write("SIGTERM trapped\n");
});
console.log(`pid ${process.pid}`);
setInterval(() => {}, 1000);
