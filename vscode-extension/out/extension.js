"use strict";
/**
 * Vibe Protect — VS Code extension.
 *
 * Shells out to the Python CLI (`vibe-protect --file - --json`) so there
 * is a single source of truth for detection logic across the web
 * playground, the desktop app, the Chrome extension, and now the IDE.
 * We intentionally don't reimplement the pattern library in TypeScript:
 * one regex change in `cli/patterns.py` propagates everywhere on the
 * next `pip install vibe-protect --upgrade`.
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const child_process_1 = require("child_process");
/**
 * Pipe `text` to the vibe-protect CLI via stdin and parse its JSON
 * output. Rejects with a human-readable error message suitable for
 * direct display in a VS Code notification.
 */
function scanText(text) {
    const cfg = vscode.workspace.getConfiguration("vibeProtect");
    const cliPath = cfg.get("cliPath", "vibe-protect");
    const advanced = cfg.get("advanced", false);
    const args = ["--file", "-", "--json"];
    if (advanced)
        args.push("--advanced");
    return new Promise((resolve, reject) => {
        let child;
        try {
            child = (0, child_process_1.spawn)(cliPath, args, { stdio: ["pipe", "pipe", "pipe"] });
        }
        catch (e) {
            reject(new Error(`Couldn't launch '${cliPath}'. Install it with 'pip install vibe-protect' ` +
                `or set 'vibeProtect.cliPath' in settings. (${e.message})`));
            return;
        }
        let stdout = "";
        let stderr = "";
        child.stdout.setEncoding("utf8");
        child.stderr.setEncoding("utf8");
        child.stdout.on("data", (d) => (stdout += d));
        child.stderr.on("data", (d) => (stderr += d));
        child.on("error", (err) => reject(new Error(`Couldn't launch '${cliPath}'. Install it with 'pip install vibe-protect' ` +
            `or set 'vibeProtect.cliPath' in settings. (${err.message})`)));
        child.on("close", (code) => {
            // exit code 0 = clean, 1 = secrets found, 2 = I/O error — JSON present in all three
            if (code !== 0 && code !== 1) {
                reject(new Error(`vibe-protect exited with code ${code}. ` +
                    (stderr.trim() || "No error details on stderr.")));
                return;
            }
            try {
                resolve(JSON.parse(stdout));
            }
            catch (e) {
                reject(new Error(`Couldn't parse vibe-protect output as JSON. ` +
                    `Raw stdout: ${stdout.slice(0, 200)}`));
            }
        });
        child.stdin.end(text, "utf8");
    });
}
// ------------------------------------------------------------------ //
// Commands
// ------------------------------------------------------------------ //
async function redactSelection() {
    const editor = vscode.window.activeTextEditor;
    if (!editor)
        return;
    const sel = editor.selection;
    if (sel.isEmpty) {
        vscode.window.showInformationMessage("Vibe Protect: select some text to redact first.");
        return;
    }
    const text = editor.document.getText(sel);
    try {
        const result = await scanText(text);
        if (result.secrets_found === 0) {
            vscode.window.setStatusBarMessage("$(shield) Vibe Protect — selection is clean", 3000);
            return;
        }
        await editor.edit((b) => b.replace(sel, result.redacted));
        vscode.window.showWarningMessage(`Vibe Protect redacted ${result.secrets_found} secret(s): ${summarise(result)}`);
    }
    catch (e) {
        vscode.window.showErrorMessage(e.message);
    }
}
async function copyScrubbed() {
    const editor = vscode.window.activeTextEditor;
    if (!editor)
        return;
    const sel = editor.selection;
    const text = editor.document.getText(sel.isEmpty ? undefined : sel);
    try {
        const result = await scanText(text);
        await vscode.env.clipboard.writeText(result.redacted);
        const msg = result.secrets_found > 0
            ? `Copied scrubbed text — ${result.secrets_found} secret(s) masked: ${summarise(result)}`
            : "Copied — nothing to redact.";
        vscode.window.setStatusBarMessage(`$(shield) Vibe Protect: ${msg}`, 4000);
    }
    catch (e) {
        vscode.window.showErrorMessage(e.message);
    }
}
async function scanActiveFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor)
        return;
    const text = editor.document.getText();
    try {
        const result = await scanText(text);
        if (result.secrets_found === 0) {
            vscode.window.setStatusBarMessage("$(shield) Vibe Protect — file is clean", 4000);
            return;
        }
        vscode.window.showWarningMessage(`Vibe Protect found ${result.secrets_found} secret(s) in ${editor.document.fileName.split("/").pop()}: ${summarise(result)}`);
    }
    catch (e) {
        vscode.window.showErrorMessage(e.message);
    }
}
function summarise(result) {
    const counts = {};
    for (const d of result.detections) {
        counts[d.pattern] = (counts[d.pattern] || 0) + 1;
    }
    return Object.entries(counts)
        .map(([k, v]) => `${k}×${v}`)
        .join(", ");
}
// ------------------------------------------------------------------ //
// Activation
// ------------------------------------------------------------------ //
function activate(context) {
    context.subscriptions.push(vscode.commands.registerCommand("vibeProtect.redactSelection", redactSelection), vscode.commands.registerCommand("vibeProtect.copyScrubbed", copyScrubbed), vscode.commands.registerCommand("vibeProtect.scanActiveFile", scanActiveFile));
    // Optional scan-on-save: only run when explicitly enabled in settings.
    context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(async (doc) => {
        const cfg = vscode.workspace.getConfiguration("vibeProtect");
        if (!cfg.get("scanOnSave", false))
            return;
        if (doc.uri.scheme !== "file")
            return;
        try {
            const result = await scanText(doc.getText());
            if (result.secrets_found > 0) {
                vscode.window.showWarningMessage(`Vibe Protect: ${result.secrets_found} secret(s) in ${doc.fileName.split("/").pop()} (${summarise(result)})`);
            }
        }
        catch {
            // swallow on-save errors; user will see them if they invoke explicitly
        }
    }));
}
function deactivate() {
    /* no-op */
}
//# sourceMappingURL=extension.js.map