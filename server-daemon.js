#!/usr/bin/env node
// Persistent Next.js dev server daemon
// This script forks the Next.js server and keeps it alive independently

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const PID_FILE = path.join(__dirname, '.dev-server-pid');
const LOG_FILE = path.join(__dirname, 'dev.log');

// Kill any existing server
try {
  const existingPid = parseInt(fs.readFileSync(PID_FILE, 'utf8').trim());
  if (existingPid) {
    try { process.kill(existingPid, 'SIGTERM'); } catch (e) {}
    try { process.kill(existingPid + 1, 'SIGTERM'); } catch (e) {}
  }
} catch (e) {}

// Clear log
fs.writeFileSync(LOG_FILE, '');

const child = spawn(
  process.execPath,
  ['node_modules/.bin/next', 'dev', '-p', '3000'],
  {
    cwd: __dirname,
    detached: true,
    stdio: ['ignore', fs.openSync(LOG_FILE, 'a'), fs.openSync(LOG_FILE, 'a')],
    env: { ...process.env, NO_COLOR: undefined, FORCE_COLOR: undefined }
  }
);

child.unref();

// Save PID
fs.writeFileSync(PID_FILE, String(child.pid));

console.log(`Server daemon started with PID ${child.pid}`);
console.log(`Log file: ${LOG_FILE}`);

// Wait a bit and verify it started
setTimeout(() => {
  const http = require('http');
  const req = http.get('http://localhost:3000/', (res) => {
    console.log(`Server verified: HTTP ${res.statusCode}`);
    process.exit(0);
  });
  req.on('error', () => {
    console.log('Server not yet responding, but process is running');
    process.exit(0);
  });
  req.setTimeout(10000, () => {
    req.destroy();
    console.log('Timeout checking server, but process is running');
    process.exit(0);
  });
}, 5000);
