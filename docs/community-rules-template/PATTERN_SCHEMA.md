# Pattern schema

The Vibe Protect CLI enforces the following schema on every fetched bundle.
Bundles that fail validation are silently ignored — the app keeps running on
the bundled + previously-cached patterns.

## Top-level

```json
{
  "version": "2.0.0",              // REQUIRED · semver, ≥ 2.0.0, monotonically increasing
  "description": "…",              // optional · human-readable changelog line
  "updated": "2026-01-20",         // optional · ISO date of last change
  "patterns": [ … ]                // REQUIRED · array, max 200 entries for community / 500 for signed CDN
}
```

## Per pattern

```json
{
  "name": "sentry_auth_token",     // REQUIRED · [a-z0-9_]+, unique within the bundle
  "regex": "\\bsntrys_[…]+\\b",    // REQUIRED · valid Python regex, ≤ 512 chars, passes the ReDoS heuristic
  "description": "…",              // required-ish · shown in UIs
  "example": "…",                  // required-ish · obviously-fake sample — NEVER a real secret
  "submitted_by": "@handle",       // optional · GitHub handle of submitter
  "pr": "https://…",               // optional · link to the merge PR for provenance
  "notes": "…"                     // optional · false-positive caveats, usage hints
}
```

## Rejection rules

| Reason | Action |
| ------ | ------ |
| Top-level not an object | entire bundle rejected |
| `version` missing or older than local cache | rejected (rollback protection) |
| `version` below `2.0.0` | rejected |
| `patterns` not an array | rejected |
| > 200 patterns (community) / > 500 (signed) | rejected |
| Pattern `name` or `regex` missing/non-string | that pattern skipped |
| Regex source > 512 chars | that pattern skipped |
| Regex contains catastrophic-backtracking shape `(x+)+` / `(.*)*` / `(x\|y)+\|(x\|y)+` | that pattern skipped |
| Regex fails to compile | that pattern skipped |
| `name` collides with a higher-priority tier (bundled, signed) | that pattern skipped — never shadows |

All bundles fetched at runtime are **additive only**. No fetched rule can
remove, shadow, or weaken a bundled rule.
