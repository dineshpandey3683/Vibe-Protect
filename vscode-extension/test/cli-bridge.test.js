/**
 * End-to-end sanity test for the VS Code extension's CLI bridge.
 *
 * We can't boot a real VS Code host in this container, so we directly
 * exercise the same `spawn('vibe-protect', ['--file', '-', '--json'])`
 * contract the compiled extension uses. If this passes, the real
 * extension's `scanText()` will work byte-for-byte the same way.
 *
 * Run:    node test/cli-bridge.test.js
 */

const { spawn } = require("child_process");
const assert = require("assert");

const CLI = process.env.VIBE_PROTECT_CLI || "/tmp/vp_venv/bin/vibe-protect";

function scanText(text, opts = {}) {
  const args = ["--file", "-", "--json"];
  if (opts.advanced) args.push("--advanced");
  return new Promise((resolve, reject) => {
    const child = spawn(CLI, args, { stdio: ["pipe", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0 && code !== 1) {
        return reject(new Error(`exit ${code}: ${stderr}`));
      }
      try {
        resolve({ code, result: JSON.parse(stdout) });
      } catch (e) {
        reject(new Error(`bad JSON: ${stdout.slice(0, 200)}`));
      }
    });
    child.stdin.end(text, "utf8");
  });
}

(async () => {
  // 1. Clean text → exit 0, zero matches
  {
    const { code, result } = await scanText("def add(a, b): return a + b\n");
    assert.strictEqual(code, 0, "clean text should exit 0");
    assert.strictEqual(result.secrets_found, 0);
    assert.strictEqual(result.exit_code, 0);
    console.log("  ✓ clean text exits 0");
  }

  // 2. Dirty text → exit 1, redacted payload has mask, no plaintext
  {
    const secret = "sk-proj-qR7pK2mNvEwXzB9aLdTfYh3JwC5xPnM2vK8Bd0AbCdEfGh";
    const { code, result } = await scanText(
      `OPENAI_API_KEY = "${secret}"\nalice@example.com\n`
    );
    assert.strictEqual(code, 1, "dirty text should exit 1");
    assert.ok(result.secrets_found >= 1, "at least one secret expected");
    assert.ok(!result.redacted.includes(secret), "plaintext must not survive into `redacted`");
    // detections projection must not contain the plaintext
    for (const d of result.detections) {
      assert.ok(!JSON.stringify(d).includes(secret), "no plaintext in detection entry");
      assert.strictEqual(typeof d.pattern, "string");
      assert.strictEqual(typeof d.mask, "string");
      assert.strictEqual(typeof d.confidence, "number");
    }
    console.log("  ✓ dirty text exits 1, masks applied, no plaintext leaked");
  }

  // 3. Advanced mode flag is accepted
  {
    const { code } = await scanText("hello", { advanced: true });
    assert.strictEqual(code, 0);
    console.log("  ✓ --advanced flag accepted");
  }

  // 4. Empty input doesn't crash
  {
    const { code, result } = await scanText("");
    assert.strictEqual(code, 0);
    assert.strictEqual(result.secrets_found, 0);
    console.log("  ✓ empty input handled");
  }

  console.log("\n4/4 passed");
})().catch((e) => {
  console.error("FAIL:", e.message);
  process.exit(1);
});
