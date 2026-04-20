# Contributing a pattern to the community rules

Thanks for helping Vibe Protect catch more leaks. Community rules are
**additive and lower-priority** — they never shadow or weaken the audited
built-in patterns, and they always appear in logs prefixed with `community_`
so users can identify their origin.

## What gets accepted

**Yes:**
- Cleanly-scoped secret formats from a specific vendor/SaaS (e.g. Sentry,
  Heroku, Mailgun, PagerDuty, Datadog)
- API keys, webhook secrets, session tokens, signing secrets
- Patterns with a documented, named vendor — not "random string that might
  be a secret"

**No:**
- Generic entropy-based rules (the main app already has a catch-all for those
  when run with `--advanced`)
- Patterns you cannot provide a public-docs link for
- Patterns that overlap with a built-in (check `cli/patterns.py` first)
- Patterns wider than 200 chars of regex source (ReDoS risk)
- Patterns that can match common non-secrets (e.g. plain hex strings,
  email-like patterns, IPs — those are already covered by built-ins)

## How to submit

1. Fork [vibeprotect/community-rules](https://github.com/vibeprotect/community-rules)
2. Add your entry at the bottom of `approved_patterns.json`:

   ```json
   {
     "name": "<vendor>_<what>",
     "regex": "<your regex>",
     "description": "What this matches, in one sentence",
     "example": "a REALISTIC but FAKE example — never a real key",
     "submitted_by": "@your-gh-handle",
     "pr": "(leave blank — a maintainer fills this in)",
     "notes": "(optional) false-positive caveats"
   }
   ```

3. Bump `version` using semver: new pattern = minor bump; tightening an
   existing pattern = patch bump.
4. Run the CI locally:

   ```bash
   python cli/pattern_updater.py check_bundle docs/community-rules-template/approved_patterns.json
   ```

   This validates the schema, compiles every regex, and runs the ReDoS
   heuristic.
5. Open a PR. A maintainer will:
   - Run `approved_patterns.json` against a corpus of real open-source repos
     to measure false-positive rate
   - Confirm the regex matches the vendor's documented format
   - Merge, and fill in the `pr` field with the merge link

## Security expectations

- Never include a real key in `example`. Use obvious fakes (`AAAA`, `xxx`,
  `EXAMPLE`, etc.) — the app's entropy filter will likely skip low-entropy
  examples anyway, but don't tempt fate.
- If you discover that a previously-merged pattern is flawed, open an issue
  tagged `security`. Do not open a PR that silently removes or weakens a rule.
- Rollback protection is enforced: the app refuses any bundle whose
  `version` is lower than the last-accepted one. Decrements will fail to
  sync for users.

## Governance

- 2+ maintainer approvals required to merge
- Every PR triggers CI that checks schema + ReDoS safety
- Quarterly false-positive-rate audit on a corpus of open-source repos
- Any maintainer can revert a merge within 7 days without review if a
  pattern turns out to be too noisy in the wild
