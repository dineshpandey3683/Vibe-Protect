# Community Rules Repo Template

This folder shows what the repo at the
`VP_COMMUNITY_RULES_URL` should look like. Copy its contents to a new public
GitHub repo — e.g. `github.com/<your-org>/community-rules` — and point
`VP_COMMUNITY_RULES_URL` at the raw `main` branch of `approved_patterns.json`:

    https://raw.githubusercontent.com/<your-org>/community-rules/main/approved_patterns.json

The separate repo pattern is deliberate:

- Keeps the main codebase small and review-able
- Lets you delegate "regex review" to a different set of maintainers
- GitHub's PR workflow becomes your moderation UI (no extra infra)
- Reviewers can run CI against submitted patterns (compile check, ReDoS
  heuristic, false-positive corpus) before merging

Files
-----
- `approved_patterns.json` — the single source of truth fetched by the app
- `CONTRIBUTING.md` — step-by-step for PR submitters
- `PATTERN_SCHEMA.md` — strict schema reference matching what the app validates

See each file for details.
