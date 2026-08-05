---
description: Phase 5 — empirical config validation. Drive the remove → observe → restore loop that proves every directive in a marketplace app's shipped config templates is load-bearing, consciously defensive, or dead code. Outputs a PR-ready markdown matrix. Requires a live deployed --instance. User-invoked only.
disable-model-invocation: true
arguments: [app, --targets, --instance]
---

# Empirical Config Validation (Phase 5)

Drive the remove → observe → restore loop that proves every directive in a marketplace app's shipped config templates is either load-bearing or consciously defensive. Output is a markdown matrix suitable for pasting into the PR description.

## Usage
```
/validate-config <app> [--targets PATH...] --instance IP
```
Parse `--targets` and `--instance` from `$ARGUMENTS`; `$app` is the first positional.

## Arguments
- `app`: Name of the marketplace app (e.g., `linode-marketplace-hashicorp-nomad`).
- `--targets PATH...`: One or more config templates to validate. Defaults to every `*.j2`, `*.conf`, `*.hcl` under `apps/<app>/roles/`.
- `--instance IP`: A live deployed instance to validate against. **Required.** Validation must run against a real running deploy — not a static lint.

## Why This Exists

Marketplace app templates accumulate cargo-culted directives over time. A line that was load-bearing under nginx 1.18 + certbot 1.6 may be dead code under nginx 1.24 + certbot 2.x. Static linting can't catch this — the only reliable test is to remove the directive on a live deploy and observe whether anything breaks.

This is mandated by the **Empirical Validation Expected** section of the repo `CLAUDE.md`. Every directive in shipped templates must be either:

1. Demonstrably load-bearing (removing it produces observable failure)
2. Consciously kept as defensive insurance (with inline comment explaining why)
3. Removed

Lines fitting none of those categories are dead code. They should not ship.

## Process

### Phase 0 — Prerequisites

- A live deploy of the app reachable via SSH (the `--instance` IP).
- `.good` snapshots of the live config files saved before any mutation:
  ```bash
  ssh root@<instance> 'cp /etc/<app>/<config> /etc/<app>/<config>.good'
  ssh root@<instance> 'cp /etc/nginx/sites-available/<domain> /etc/nginx/sites-available/<domain>.good'
  ```
- Credentials available on the instance for authenticated API checks (typically in `/home/<sudo-user>/.credentials`).

### Phase 1 — Enumerate Directives

For each target template, list every directive that's not pure scaffolding (server blocks, top-level keys are scaffolding; the lines INSIDE them are directives). For each, design the smallest test that would prove its absence breaks something a real customer would notice.

Examples of directive categories and their typical failure modes:

| Directive class | Typical failure mode if removed |
|---|---|
| `proxy_read_timeout` | nginx 504 at default 60s on long-polling endpoints |
| `proxy_buffering off` | UI log-tail panes go silent, then burst |
| `proxy_set_header X-...` | Backend rejects request based on missing/wrong header |
| `bind_addr = "127.0.0.1"` | Service listens on `*` instead of loopback |
| `acl { enabled = true }` | API becomes anonymously accessible |
| `data_dir`, `state_dir`, etc. | Service exits on startup |
| `advertise { ... }` blocks | Multi-node refuses to start; single-node may auto-recover |
| `ui { enabled = true }` | UI route returns placeholder/404 |

### Phase 2 — Validation Loop

For each directive identified in Phase 1, on the live instance:

1. **Snapshot** — confirm `.good` exists.
2. **Mutate** — remove or invert the directive in the live config file (use `sed`, `python3 -c`, or a small inline script).
3. **Apply** — reload or restart the service:
   - nginx: `nginx -t && systemctl reload nginx`
   - systemd-managed apps: `systemctl restart <service>` then poll API until ready
4. **Exercise** — run the failing scenario:
   - For nginx directives: `curl` against a representative endpoint (blocking query, log stream, POST with auth, etc.)
   - For agent config directives: `systemctl status`, journalctl tail, API health probe
   - For security directives: anonymous request expecting 401/403
5. **Record** — capture result as `LOAD-BEARING`, `DEFENSIVE` (no observable failure but principled to keep), or `DEAD CODE`.
6. **Restore** — `cp <config>.good <config>` and reload/restart.
7. **Verify clean** — confirm baseline behavior recovers (curl returns 200, leader endpoint resolves, etc.).

### Phase 3 — Output Matrix

Produce a markdown table per template, suitable for the PR description:

```markdown
### `roles/<app>/templates/<file>.j2`

| Directive | Verdict | Evidence |
|---|---|---|
| `proxy_read_timeout 340s` | **LOAD-BEARING** | Blocking query returns 504 at 60s without it; full duration with it. |
| `proxy_buffering off` | **DEFENSIVE** | Curl test inconclusive (drains too fast); kept for slow-browser-client edge case. |
| `location /.well-known/ { ... }` | **DEAD CODE** | `certbot renew --dry-run` succeeds without it; certbot uses `authenticator = nginx`, not webroot. |
| `proxy_set_header Origin ...` | **DEAD CODE** | POST `/v1/jobs` with `Origin: https://evil.example.com` returns 200 with or without rewrite under current app version. |
```

Action items the matrix produces:

- For `DEAD CODE` rows: open a follow-up commit removing those lines from the template.
- For `DEFENSIVE` rows: confirm there's an inline comment in the template explaining the rationale; add one if missing.
- For `LOAD-BEARING` rows: no action needed, but the evidence column is the documentation.

### Phase 4 — Restore + Final Health Check

Before leaving the instance, confirm:

- Both config files match their `.good` snapshots (`diff`).
- All affected services are active (`systemctl is-active`).
- Application API responds to authenticated requests as expected.
- Any test workload deployed during validation is purged.

## Anti-Patterns to Avoid

- **Validating against a fresh-deploy without the workload.** Some directives only matter under load (streaming logs, blocking queries). Submit a representative test workload before validating proxy/buffering/timeout directives.
- **Assuming a `nginx -t` pass means a directive is correct.** `nginx -t` only checks syntax. The whole point of empirical validation is behavior under traffic.
- **Skipping restore between tests.** State drift produces false positives. Always restore from `.good` before the next mutation.
- **Treating warnings as failures or vice versa.** Read the actual error/log messages, don't infer.
- **Validating on a production instance.** Always use a throwaway test deploy for this — directive removal can break service mid-test.

## Worked Example

Suppose an app's nginx template inherited four custom directives. Empirical validation might produce a matrix like this:

| Directive | Verdict |
|---|---|
| `proxy_read_timeout 340s` | LOAD-BEARING (504 at 60s without it) |
| `proxy_buffering off` | DEFENSIVE (curl inconclusive; kept for browser UI) |
| `location /.well-known/` | DEAD CODE (certbot uses nginx authenticator) |
| `proxy_set_header Origin` | DEAD CODE (app version doesn't enforce Origin) |

The two DEAD CODE directives would then be removed, and the matrix plus the test logs that justify each verdict go into the PR description.
