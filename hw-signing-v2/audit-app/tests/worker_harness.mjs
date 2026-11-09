// Test harness: runs the REAL hw-signing Worker code (worker.js) in Node.
// Usage: node worker_harness.mjs <worker.js file URL> <secret>
// Reads one JSON job per line on stdin: {"path": "/sign"|"/verify", "body": {...}}
// Writes one JSON line per job: {"status": n, "json": {...}}
const worker = (await import(process.argv[2])).default;
const secret = process.argv[3];
let buf = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (d) => (buf += d));
process.stdin.on("end", async () => {
  for (const line of buf.split("\n")) {
    if (!line.trim()) continue;
    const job = JSON.parse(line);
    const req = new Request("https://worker.test" + job.path, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(job.body),
    });
    const res = await worker.fetch(req, { SIGNING_SECRET: secret });
    const json = await res.json();
    process.stdout.write(JSON.stringify({ status: res.status, json }) + "\n");
  }
});
