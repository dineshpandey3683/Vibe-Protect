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
python vibe_protect.py                    # standard mode (18 patterns)
python vibe_protect.py --advanced         # entropy-aware + catch-all + custom rules
python vibe_protect.py --init-custom-rules  # seed ~/.vibeprotect/custom_rules.json
python vibe_protect.py --log events.jsonl
python vibe_protect.py --list-patterns
python vibe_protect.py --quiet --no-notify
```

## Standard vs. Advanced mode

**Standard** runs the 18 built-in regexes as-is. Fast, deterministic, no false
negatives on real keys.

**Advanced** (`--advanced`) adds three quality-of-life layers on top:

1. **Shannon-entropy filtering** — for key/token-like patterns only, skips
   matches whose entropy is below 3.5 bits/char (kills obvious placeholders
   like `sk-YOUR_KEY_HERE`).
2. **Context filtering** — for key/token-like patterns only, skips matches on
   lines containing `example`, `sample`, `demo`, `placeholder`, `dummy`,
   `fake` (reduces noise on doc/test files).
3. **Entropy catch-all** — flags random-looking ≥24-char blobs that don't
   match any known pattern but smell like secrets.
4. **Custom rules** — loads your own regexes from `~/.vibeprotect/custom_rules.json`
   (run `--init-custom-rules` to see an annotated example).

Important: filters are applied **per pattern**. Low-entropy patterns (emails,
IPs, credit cards, shell prompts, DB URLs, PEM blocks, SSH keys) are **always**
matched regardless of entropy or context — otherwise we'd miss real secrets.

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
| `--check-update`   | Check GitHub for a newer release and exit      |
| `--no-update-check`| Skip the non-blocking update check on startup  |
| `--version`        | Print the installed version and exit           |

### Environment variables

| Variable                    | Meaning                                             |
| --------------------------- | --------------------------------------------------- |
| `VP_DISABLE_UPDATE_CHECK=1` | Fully disable the release updater (no network)     |
| `VP_UPDATE_URL`             | Override the GitHub release API URL                 |
| `VP_ENABLE_PATTERN_SYNC=1`  | Opt in to signed dynamic pattern bundles from CDN  |
| `VP_PATTERN_URL`            | Override the pattern-bundle CDN origin              |
| `VP_SIGNING_PUBKEY_PEM`     | Override the bundled Ed25519 public key             |
| `VP_CACHE_DIR`              | Override the cache dir (default `~/.vibeprotect/`)  |

The updater **never downloads or executes** a release asset automatically.
When a newer version is available it prints a banner with the release URL and
the suggested `pip install --upgrade` command — you review and install it
yourself.
