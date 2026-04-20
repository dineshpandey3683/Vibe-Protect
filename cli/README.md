# Vibe Protect — CLI

Terminal clipboard guardian. Watches your clipboard and auto-redacts secrets
**before** they reach a chat window, ticket, doc, or LLM prompt.

## Install

```bash
cd cli
pip install -r requirements.txt
```

> **Linux note:** pyperclip needs a clipboard backend — `sudo apt install xclip`
> (or `xsel`) on most distros. macOS & Windows work out of the box.

## Run

```bash
python vibe_protect.py                 # monitor with defaults
python vibe_protect.py --log events.jsonl
python vibe_protect.py --list-patterns
python vibe_protect.py --quiet --no-notify
```

## What it catches

- OpenAI / Anthropic API keys (`sk-…`, `sk-ant-…`)
- AWS access keys (`AKIA…`) and quoted secret keys
- GitHub PATs (`ghp_…`, `gho_…`, `ghs_…`)
- Stripe keys (`sk_live_…`, `pk_test_…`)
- Google / Firebase API keys (`AIza…`)
- Slack tokens (`xoxb-…`)
- JWTs
- PEM private key blocks (RSA / EC / OpenSSH / PGP)
- SSH public keys
- Database URLs with embedded credentials
- Emails, IPv4 addresses, credit cards, shell prompts
- `password="…"`, `api_key="…"` style assignments
- Long base64 blobs

See `python vibe_protect.py --list-patterns` for the full live list.

## Flags

| Flag               | Meaning                                        |
| ------------------ | ---------------------------------------------- |
| `--log FILE`       | Append each redaction event as JSONL to FILE   |
| `--quiet`          | No console output                              |
| `--no-notify`      | Disable desktop notifications                  |
| `--interval 0.3`   | Clipboard polling interval in seconds          |
| `--list-patterns`  | Print the active pattern library and exit      |
