<div align="center">

# ▍ vibe·protect

**A clipboard guardian for developers in the AI era.**

Stop pasting API keys, private keys, DB URLs, tokens, and internal IPs into
ChatGPT, Slack DMs, GitHub issues, and support tickets. Vibe Protect watches
your clipboard and auto-redacts secrets **before** they reach the other side.

`CLI · Desktop GUI · Browser Extension · Web Playground`

![license](https://img.shields.io/badge/license-MIT-facc15?style=flat-square)
![python](https://img.shields.io/badge/python-3.9+-0A0A0A?style=flat-square)
![manifest](https://img.shields.io/badge/manifest-v3-0A0A0A?style=flat-square)
![telemetry](https://img.shields.io/badge/telemetry-zero-facc15?style=flat-square)

</div>

---

## What it is

A single pattern library implemented four ways:

| Client             | What it does                                                                 | Path          |
| ------------------ | ---------------------------------------------------------------------------- | ------------- |
| **CLI**            | Watches your clipboard from a terminal. Notifications + JSONL event log.     | [`cli/`](cli/)           |
| **Desktop GUI**    | Native Tkinter window with live history and arm/pause toggle.                | [`desktop/`](desktop/)       |
| **Browser Extension** | Intercepts every copy/cut event in every tab. Badge counter + popup.     | [`extension/`](extension/)     |
| **Web Playground** | Paste anything, see live redaction. Also hosts dashboards + download page.   | [`frontend/`](frontend/) + [`backend/`](backend/) |

All four speak the same 18-pattern library defined in [`cli/patterns.py`](cli/patterns.py)
(Python) and mirrored in [`frontend/src/lib/patterns.js`](frontend/src/lib/patterns.js) /
[`extension/patterns.js`](extension/patterns.js).

---

## Why

Your `.env` has no business being in an LLM's context window. Neither does
your `ssh-ed25519 ...` key, your prod `DATABASE_URL`, your `sk_live_...`
Stripe key, or your teammate's email address. But when you're moving fast,
you *will* slip — and paste something you shouldn't.

Vibe Protect is the seat-belt. It redacts 18 patterns by default:

- OpenAI / Anthropic API keys
- AWS access & secret keys
- GitHub personal access tokens
- Stripe live/test keys
- Google / Firebase API keys
- Slack tokens
- JWTs
- PEM private key blocks (RSA / EC / OpenSSH / PGP)
- SSH public keys
- DB connection URLs with embedded credentials
- Emails, IPv4, credit cards
- Shell prompts (`user@host:~$`)
- Generic `PASSWORD=…` / `API_KEY=…` assignments
- Long base64 blobs

Run `python cli/vibe_protect.py --list-patterns` for the live list.

---

## Quick start

### CLI (30 seconds)

```bash
git clone https://github.com/YOUR_USERNAME/vibe-protect.git
cd vibe-protect/cli
pip install -r requirements.txt
python vibe_protect.py
```

Now copy something sensitive. Try pasting it anywhere — it's already
redacted.

### Desktop GUI

```bash
cd desktop
pip install -r requirements.txt   # pulls pyperclip
python vibe_desktop.py
```

### Browser Extension (Chrome / Edge / Brave / Arc)

1. `chrome://extensions`
2. Toggle **Developer mode** (top right)
3. **Load unpacked** → pick the `extension/` folder
4. Pin the amber shield to your toolbar

For Firefox: `about:debugging#/runtime/this-firefox` → Load Temporary Add-on → `manifest.json`.

### Web playground (dev)

```bash
# backend
cd backend
pip install -r requirements.txt
# env: MONGO_URL, DB_NAME required
uvicorn server:app --reload --port 8001

# frontend (separate shell)
cd frontend
yarn install
yarn start
```

Open [http://localhost:3000](http://localhost:3000).

---

## Repo layout

```
vibe-protect/
├── cli/              # Python CLI (single source of truth for patterns)
│   ├── patterns.py
│   ├── vibe_protect.py
│   ├── requirements.txt
│   └── README.md
├── desktop/          # Tkinter GUI
│   ├── vibe_desktop.py
│   ├── requirements.txt
│   └── README.md
├── extension/        # Browser extension (Manifest v3)
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── popup.html / popup.js / popup.css
│   ├── options.html / options.js
│   ├── patterns.js
│   ├── icons/
│   └── README.md
├── backend/          # FastAPI API
│   └── server.py
├── frontend/         # React landing + dashboard
│   └── src/
├── LICENSE
└── README.md
```

---

## API reference

The backend exposes a small JSON API, useful if you want to wire the
redaction engine into other tools.

| Method | Route           | Description                                              |
| ------ | --------------- | -------------------------------------------------------- |
| GET    | `/api/`         | Health check                                             |
| GET    | `/api/patterns` | List all active patterns + examples                      |
| POST   | `/api/redact`   | `{ text }` → `{ cleaned, matches, chars_before/after }`  |
| POST   | `/api/track`    | Opt-in anonymous event counter (source, patterns, sizes) |
| GET    | `/api/feed`     | Last N anonymised events for the live ticker             |
| GET    | `/api/stats`    | Aggregate counts powering the dashboard                  |

Example:

```bash
curl -s -X POST https://your-host/api/redact \
  -H 'content-type: application/json' \
  -d '{"text":"OPENAI_API_KEY=sk-proj-abcd1234efgh5678ijkl9012mnop3456"}'
```

---

## Contributing

PRs welcome — especially:

- New patterns (add to `cli/patterns.py` **and** `frontend/src/lib/patterns.js` + `extension/patterns.js`)
- Tray-icon support for the desktop app (`pystray`)
- A Safari port of the extension
- Tests — there are currently none; regex false-positive detection would be huge

---

## Privacy

- **CLI, desktop, extension:** zero network calls. All matching is local.
- **Web playground:** the `/api/redact` endpoint stores *counts only*
  (which patterns matched, how many chars). Never the original text, never
  the redacted text, never an IP, never a user identifier.

---

## License

MIT. See [LICENSE](LICENSE).

---

<div align="center">
<sub>Built for devs who paste too fast. ❂</sub>
</div>
