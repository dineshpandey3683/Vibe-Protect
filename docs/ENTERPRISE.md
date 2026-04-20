# Enterprise deployment guide

For IT / security teams rolling Vibe Protect out to a fleet. All control lives
in a single YAML policy file pushed via your existing GPO / MDM / config-mgmt
channel.

## Deployment targets

| Platform | Push via | Policy path |
| --- | --- | --- |
| Windows | GPO / Intune / SCCM file-copy, or registry keys | `C:\ProgramData\VibeProtect\policy.yaml` **or** `HKLM\Software\Policies\VibeProtect\*` |
| macOS | MDM config profile (custom YAML payload) | `/Library/Application Support/VibeProtect/policy.yaml` |
| Linux | Ansible / Chef / Puppet / Salt | `/etc/vibeprotect/policy.yaml` |

Precedence (highest wins):

1. Fields listed in machine policy's `enforced_fields` — **immutable by users**
2. Machine policy (any unfenced field)
3. Windows Registry `HKLM\Software\Policies\VibeProtect\*`
4. User config (`~/.vibeprotect/config.yaml` or platform equivalent)
5. Hard-coded safe defaults

## Two-minute setup

1. Copy the template:

   ```bash
   cp docs/enterprise-policy.sample.yaml /etc/vibeprotect/policy.yaml   # Linux
   ```

2. Edit for your org (disable irrelevant patterns, list required AAD groups,
   set `enforced_fields`).

3. On any endpoint, verify the roll-out:

   ```bash
   python vibe_protect.py --show-policy
   ```

   Output includes the source trace — so you can tell at a glance which file
   actually won.

## SSO wiring

Vibe Protect verifies JWT ID tokens against your IdP's JWKS — kid-indexed, so
key rotation is handled automatically. Supported providers:

| Provider | `sso_provider` | `sso_tenant_id` |
| --- | --- | --- |
| Azure AD / Entra | `azure` | Tenant UUID |
| Okta | `okta` | Okta domain, e.g. `acme.okta.com` |
| Google Workspace | `google` | (not required — uses hosted JWKS) |

Always set `sso_client_id` to your app registration's client_id so the JWT's
`aud` claim can be validated. Optionally override `sso_jwks_url` for sovereign
clouds (Gov, DE, CN).

Optional dep (runtime): `pip install pyjwt cryptography requests`. If PyJWT
is missing, SSO fails closed and audit-logs the reason.

## Audit evidence for SOC2 / HIPAA / GDPR / PCI

- `audit_level: verbose` writes one AES-256-GCM-encrypted, HMAC-authenticated
  line per redaction + policy event
- `python vibe_protect.py --audit-verify` — tamper-evidence on-demand
- `python vibe_protect.py --audit-report json > report.json` — aggregate
  report over every entry on disk (not just the session)
- `python vibe_protect.py --audit-report csv` — drop into Splunk / Datadog /
  Chronicle

See [`../cli/audit_logger.py`](../cli/audit_logger.py) for the full crypto
disclaimer. Short version: we use FIPS-approved algorithms (AES-256-GCM,
HMAC-SHA256, HKDF, PBKDF2). Actual FIPS 140-2 *certification* requires a
validated module (RHEL FIPS, CNG, BoringCrypto) — install those on your
endpoints if you need the paperwork.

## Dependencies

The enterprise features degrade gracefully:

| Missing dep | Effect |
| --- | --- |
| `pyyaml` | Policy must be JSON (with a `.yaml` extension — we parse JSON as a YAML subset) |
| `pyjwt` + `requests` | SSO disabled (fails closed, audit-logged) |
| `cryptography` | Audit logger disabled (required for AES-GCM + HKDF) |

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `--show-policy` shows only "sources: defaults" | policy file not in the expected path — double-check with `enterprise_config.py paths` |
| User can still pause protection | `pause_allowed` wasn't listed in `enforced_fields` |
| SSO always denies | check `audit-report` filtered to `SSO_AUTH`; the `reason` metadata field explains why |
| Malformed YAML silently ignored | run `python vibe_protect.py --show-policy`; check stderr for `ignored malformed policy at …` |
