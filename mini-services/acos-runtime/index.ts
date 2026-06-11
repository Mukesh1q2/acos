import { spawn } from "child_process";
import { createServer } from "http";

const PORT = 3031;
const ACOS_PATH = "/home/z/my-project/acos-runtime";

// Start the ACOS Runtime FastAPI server using uvicorn
const uvicorn = spawn("/home/z/.venv/bin/uvicorn", [
  "acos.api.server:app",
  "--host", "0.0.0.0",
  "--port", String(PORT),
  "--reload",
  "--reload-dir", `${ACOS_PATH}/acos`,
], {
  cwd: ACOS_PATH,
  stdio: ["pipe", "pipe", "pipe"],
  env: {
    ...process.env,
    PYTHONPATH: ACOS_PATH,
  },
});

uvicorn.stdout.on("data", (data: Buffer) => {
  console.log(`[acos-stdout] ${data.toString().trim()}`);
});

uvicorn.stderr.on("data", (data: Buffer) => {
  console.log(`[acos-stderr] ${data.toString().trim()}`);
});

uvicorn.on("close", (code) => {
  console.log(`[acos] Process exited with code ${code}`);
  process.exit(code ?? 1);
});

// Health check endpoint
const healthServer = createServer((req, res) => {
  res.writeHead(200, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ status: "ok", service: "acos-runtime", port: PORT }));
});

healthServer.listen(3032, () => {
  console.log(`[acos-health] Health check on port 3032`);
});

process.on("SIGTERM", () => {
  uvicorn.kill();
  healthServer.close();
  process.exit(0);
});

process.on("SIGINT", () => {
  uvicorn.kill();
  healthServer.close();
  process.exit(0);
});
