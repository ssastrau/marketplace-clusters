---
description: Backend tests — generate Pytest backend regression tests for a Marketplace app that has NO web UI (headless / API-only apps — databases, caches, message brokers, VPNs, vector stores, exporter agents). Deploys its own box via the Linode MCP, probes the live service over SSH (and its HTTP API where one exists), generates Service Object Model test files matching the suite's conventions, then verifies the full suite on a fresh redeploy. The complement of /ui-regression-tests: that skill handles browser apps, this one handles everything it rejects. Runs in pipeline mode (after /validate-config) or standalone (operator supplies the inputs). User-invoked only.
disable-model-invocation: true
arguments: [app, --scenarios]
---

# Backend Regression Tests (Generate Live-Probed Service Tests)

Generate Pytest backend tests for a Linode Marketplace app that has **no browser UI** by probing a
**live deployed service** first — over SSH (the app's own client / CLI) and its HTTP API where one
exists — then producing real, grounded Service Object Model (SOM) test files that match the existing
`tests/regression_tests/` suite conventions, and proving them with a **full suite pass on a fresh
redeploy**.

It deploys its own boxes by running the app's deploy script on a fresh box — the same way CI does —
so it only needs the app's playbook + deploy script to exist (and, for unpublished apps, the working
branch to be pushed).

**Scope: headless / API-only apps.** These are *service* tests, driven over SSH and HTTP — databases
(`postgresql`, `mysql`, `redis`, `valkey`, `pgvector`), message brokers (`nats-single-node`), vector
stores (`chroma`, `weaviate`), VPN / network services (`wireguard-server`, `openvpn`, `shadowsocks`),
LLM-serving APIs (`ollama`), and headless exporter/agent apps. Apps with a real web UI are the **other
skill's** job — this skill is the exact complement of `/ui-regression-tests`, which STOPs on headless
apps and points here. The skill checks this up front (Step 1) and stops if the app actually has a
browsable UI as its primary surface.

## Usage
```
/backend-regression-tests <app> [--scenarios "<free text>"]
```
Parse `--scenarios` from `$ARGUMENTS`; `$app` is the first positional.

## Arguments
- `<app>`: the full Marketplace directory suffix under `apps/`, **hyphenated**, exactly as deployed
  (e.g. `redis`, `wireguard-server`, `nats-single-node`). Used for
  `tests/regression_tests/apps/linode-marketplace-<app>/`.
- `--scenarios "<free text>"`: optional plain-language description of what to test beyond the
  service-up/reachable baseline. When omitted, scenarios come from the artifact discovery in Step 2
  (pipeline mode) or the operator (standalone mode).

## Two modes (detected at Step 1, from whether `STATE.md` exists)

- **Pipeline mode** — `.documentation/<app>/STATE.md` exists (run after `/validate-config`):
  the working branch (`GH_USER`/`BRANCH` for the deploy) and scenarios are discovered from
  `STATE.md` and the phase artifacts, with a single operator confirmation of the scenario list.
- **Standalone mode** — no `STATE.md`: the operator supplies the scenarios (via `--scenarios`,
  or asked); the deploy defaults to `akamai-compute-marketplace` / `main` unless the operator wants
  a fork/branch tested. Collect every missing input in **one message** — don't drip-feed questions.

Either way the access model is identical: the skill deploys its own boxes.

## Hard stops — no indefinite loops (non-negotiable)

When anything is **unclear**, an **input is missing**, or a **bounded retry is exhausted**, the
skill STOPS: it reports where it is, what it has, and exactly what it needs — then waits for the
operator. It never guesses past a gap, never improvises a workaround, and never keeps retrying
"one more time." The hard stops, with their bounds:

| Condition | Bound |
|---|---|
| Linode MCP not available | stop immediately (Step 1) |
| App has a real web UI as its primary surface | stop at Step 1 — use `/ui-regression-tests` instead |
| Scenarios missing or too vague to test from | stop and ask once (Steps 1–2); unanswered → stay stopped |
| Working branch not pushed (when testing unmerged code) | stop; operator pushes (Step 3) |
| Deploy (or redeploy) fails | stop immediately — **zero** debug/fix attempts (Steps 3, 7b) |
| Deploy still not finished while monitoring | **30 min** from boot, then treat as a failed deploy (Step 3) |
| Service unreachable / client not on box / port state unexplained | stop and ask (Steps 4–5) |
| Test failures while iterating | **2** fix attempts, then stop (Step 7a) |
| Fresh-redeploy verification still failing | **2** redeploy cycles, then stop (Step 7b) |

A stop is not a failure of the skill — it's the designed outcome whenever the path forward isn't
certain. Resuming after the operator answers is always fine.

## Access model

The skill deploys its own boxes via the `linode-team` MCP, so it already has everything it needs:

- **Box + root password** — every box is created with `mcp__linode-team__create_linode`, a **root
  password the skill generates** at deploy time, and the **operator's SSH pubkey** via
  `authorized_keys` (same provisioning pattern as `/app-deploy`). The IP comes from the create/
  `get_linode` response. These same values are the `LINODE_IPV4` / `LINODE_ROOT_PASS` the pytest
  run needs (the suite's global `ssh_credentials` fixture reads them from env —
  `tests/regression_tests/conftest.py`), passed inline to the command.
- **Skill-driven box reads AND the tests themselves run commands over SSH.** Unlike the UI skill
  (which drives a browser at the public URL), backend checks execute the app's own client **on the
  box** — because headless services are routinely bound to `localhost` or firewalled, so the test
  runner's laptop usually can't reach them. The suite's `remote_exec` fixture (Step 6) runs every
  such command through key-or-password SSH; the operator's pubkey is on the box because the skill
  put it there, and the pytest run authenticates with the generated root pass over `paramiko`.
  **Because backend tests run SSH on every test** (not just once for a credentials read, as the
  browser suite does), runtime root-SSH must actually work. If the app's `test-vars.sh` sets
  `DISABLE_ROOT`, password root login is off — set `LINODE_ROOT_USER` to the app user in the pytest
  command and confirm that user can run the probe commands (via `sudo` where needed). See the
  `troubleshooting.md` entry.
- **App credentials** — read from the box's credentials file over SSH (Step 4), used to drive the
  live probe and referenced in tests by **key name** via the `app_credentials` fixture. Never
  hardcoded into a test, never written to the artifact.
- Don't echo the generated root password or app credential **values** into chat text or artifacts
  beyond what tool calls inherently show.

## Grounding contract (non-negotiable)
Tests are written from what the live service actually does — never from memory or guesswork:
- Every command, expected output, port, and API response comes from a **real probe** of the deployed
  service (Step 5): you ran `redis-cli ping` and saw `PONG`; you ran `ss -tlnp` and saw the port
  bound; you `curl`ed the heartbeat and saw the JSON. A guessed command output is a test that fails
  on first run.
- Scenarios presented to the operator in Step 2 cite the artifact they came from
  (`e2e_testing.md`, `manual_install.md`, …) — never invented from memory of the app.
- The pass condition is empirical: the full suite green against a **fresh deploy** (Step 7).
- If the live service can't be reached, its client isn't on the box, or a port's state can't be
  explained (open vs. firewalled), **STOP and ask the operator.** Do not fabricate a test against
  imagined behavior.

## Flow overview

```
1. Prerequisites        →  Linode MCP connected? App is headless (else STOP → /ui-regression-tests)? Detect mode (STATE.md?); standalone → collect inputs
2. Establish scenarios  →  --scenarios, or pipeline artifacts + operator confirms, or operator-provided (standalone)
3. Deploy the app       →  Empty box + the app's deploy script (test-vars.sh + <app>-deploy.sh, like CI), monitor
                           deploy fails → STOP and report; fixing the deployment is the operator's job
4. SSH into VM          →  Read /etc/motd (App URL if any) + credentials file (login/API keys)
5. Probe the service    →  Over SSH: unit status, listening ports, client commands; over HTTP: API endpoints. Capture real output
6. Generate test files  →  SOM service classes + test_scenarios.py + conftest.py (+ shared remote_exec/http_session once)
7. Run tests            →  Iterate on the exploration box, then REDEPLOY fresh and pass the full suite clean
8. Record failure modes →  Append confirmed, novel issues to troubleshooting.md
9. Record artifact      →  Summarize the run in .documentation/<app>/backend_testing.md; pipeline mode: update STATE.md
```

## On any error — check `troubleshooting.md` first (standing rule)

**This applies at _every_ step, not just the test run** — the entries span SSH reads, service
probing, and the pytest run. The moment any command fails, **read `troubleshooting.md` and look for
the matching symptom before improvising a fix.** If the symptom is listed, apply the documented fix;
only if it isn't do you diagnose from scratch. New, confirmed, novel failures get appended back per
Step 8.

## Test suite conventions

Understanding these upfront avoids generating code that doesn't fit the project.

**Placeholders used throughout this skill:**
- `{app}` — see `<app>` above (hyphenated directory suffix).
- `{pkg}` — the Python package name under `services/`. **Derived automatically, in this order:**
  (1) if `tests/regression_tests/services/` already contains a folder for this app, reuse it;
  (2) else if `tests/regression_tests/pages/` already has one for this app (a browser suite already
  exists — e.g. `nats-single-node` → existing `nats`), **reuse that same name** so `services/` and
  `pages/` stay aligned for the same app; (3) else use `{app}` with hyphens replaced by underscores
  (`wireguard-server` → `wireguard_server`). Must be a valid Python identifier.
- `{App}` — PascalCase class prefix for service objects (e.g. `Redis`, `Postgres`, `WireGuard`).
- `{Feature}` — PascalCase name of a probed capability (rarely needed — most headless apps are one
  service object named `{pkg}_service.py` with class `{App}Service`). Use it only when an app
  genuinely has two distinct surfaces: name the extra file `{pkg}_{feature}_service.py` with class
  `{App}{Feature}Service` (e.g. a broker with both a client protocol and a monitoring API →
  `nats_service.py` + `nats_monitoring_service.py`).

```
tests/regression_tests/
├── conftest.py                          # global fixtures — do NOT redefine these
├── utils/
│   └── ssh.py                           # run_remote_command lives here (add once; reuse after)
├── services/                            # ← backend analog of pages/ (this skill owns it)
│   ├── __init__.py                      # package-level init (add once, like pages/__init__.py)
│   └── {pkg}/
│       ├── __init__.py
│       └── {pkg}_service.py             # client/CLI/API actions — NO assertions
└── apps/
    └── linode-marketplace-{app}/
        ├── conftest.py                  # app-specific: credentials_file_path, base_url (if it has an API)
        └── test_scenarios.py
```

**Baseline tests.** The **first test in every backend suite verifies the app is up AND working** —
not merely installed, but responding. It is always generated and always comes first:
- a **service** → its unit/container is active *and* it answers a basic health/liveness probe (a
  heartbeat/ping/`SELECT 1`, whichever the archetype gives) — "active" alone can hide a process that
  started but isn't serving;
- a **library / CLI** (no service) → its entrypoint actually runs, e.g. `<tool> --version` / `import
  <pkg>` succeeds in the venv.

After that, a **port-listening** test is generated whenever the app binds a port worth asserting on,
and its assertion reflects the observed **firewall posture** (publicly listening vs. loopback-only —
a loopback bind is correct, not a failure; see the archetype table). Everything past the baseline
comes from the confirmed scenarios (Step 2).

**Global fixtures already defined — never redefine in app conftest:**
- `ssh_credentials` — reads `LINODE_IPV4`, `LINODE_ROOT_USER`, `LINODE_ROOT_PASS` from env
- `app_credentials` — SSHes into VM, parses credentials file as `Key: Value` pairs
- `remote_exec` — **added by this skill** (Step 6): a callable bound to `ssh_credentials` that runs a
  command on the VM and returns `(stdout, stderr, exit_code)`. This is the backbone of backend tests
  and the reason they don't need a browser. Add it to the global `conftest.py` + `utils/ssh.py` the
  first time; **reuse it** ever after — never redefine it per app.
- `http_session` — **added by this skill** (Step 6): a `requests.Session` with `verify=False` (test
  deploys use self-signed certs) for apps that expose an HTTP API. Add once globally; reuse after.
- `context` / `browser` — the browser fixtures the UI suite uses. **Backend tests never request
  them**, so no Chromium launches (the failure-screenshot hook already no-ops when neither `page`
  nor `context` is present — `conftest.py`). Don't import Playwright in a backend test.

## Backend archetypes — what "works" means per app shape

The confirmed scenarios (Step 2) drive the specifics, but every headless app maps to one of these
shapes. Use it to know what to probe in Step 5 and which baseline + functional checks to generate.
**Never assume the values — probe them live (Step 5) and assert on what you actually saw.**

| Archetype (reference-apps bucket) | Liveness baseline | Functional check(s) | Vantage |
|---|---|---|---|
| Relational DB — `postgresql`, `mysql`, `pgvector` (9, 2) | unit active; port state matches firewall | auth + `SELECT 1` with real creds; pgvector: `CREATE EXTENSION vector` / a vector op | SSH (client on box) |
| KV / cache — `redis`, `valkey` (9) | unit active; port state | `PING`→`PONG`; `AUTH` with cred key; `SET`/`GET` roundtrip | SSH |
| Vector DB API — `chroma`, `weaviate` (2) | unit/container up | heartbeat / ready endpoint; collection create + query roundtrip | HTTP (public) or SSH `curl` (loopback) |
| Message broker — `nats-single-node` (5) | unit active | `/healthz` + `/varz` monitoring endpoints; pub/sub roundtrip via CLI | HTTP + SSH |
| VPN / network — `wireguard-server`, `openvpn`, `shadowsocks` (10) | unit active; interface up (`wg show` / `ip link`) | listening on expected UDP/TCP port; key/config file present with correct perms (e.g. `0600`) | SSH |
| LLM-serving API — `ollama` (1) | unit active | `/api/version`, `/api/tags`; (optional) a tiny generate with a long `timeout` | HTTP or SSH `curl` |
| Headless exporter / agent (11) | unit active | metrics endpoint returns Prometheus text format (`# HELP` / `# TYPE`) | HTTP or SSH `curl` |

**Vantage point is a real decision here** (the UI skill never had it — a browser always hits the
public URL). Determine it per endpoint in Step 5 from the observed firewall + bind address:
- **Loopback-bound or firewalled** → run the client / `curl` **on the box via SSH** (`remote_exec`).
  A `127.0.0.1`-only bind is a *correct* security posture for a datastore, not a bug — the test
  asserts it, it doesn't fail on it.
- **Genuinely public** (a firewall rule opens it, the app is meant to be reached remotely) → the
  HTTP checks may hit it directly from the runner via `http_session`; service/protocol checks that
  need a native client still run on the box unless that client is also on the runner.

**Verify the data round-trips — don't stop at "the op returned 200."** For a data-store app
(DB / cache / vector / broker with persistence), the functional check must **write then read back
and assert the actual data** — not merely that a create call succeeded or the service is up. A
collection that exists but can't store/retrieve, or an `INSERT` that "succeeds" but returns nothing
on `SELECT`, is a regression a status-code check misses. So:
- vector DB → add vectors, then **query and assert the expected nearest neighbour / document** comes
  back;
- relational → `INSERT`, then `SELECT` the row and assert the value;
- cache → `SET`, then `GET` and assert the value.

**Make the assertion deterministic.** When the result depends on an ML model / ranking / anything
fuzzy, feed **controlled inputs** so the outcome is exact — e.g. supply explicit embedding vectors
rather than letting the server embed text, so the nearest neighbour is fixed arithmetic, not a
model-version-dependent semantic guess.

**Not every headless app has a data surface.** Framework / library / agent apps (e.g. `crewai`)
expose no queryable datastore to round-trip — for those the functional check is liveness / version /
config only, and if there's genuinely nothing running to probe, that's a scope call to raise with
the operator, not a roundtrip to invent.

## Process

### Step 1 — Prerequisites

**Linode MCP.** Verify `mcp__linode-team__*` tools are available (`create_linode`, `get_linode`, …)
— this skill deploys its own boxes through them. If not available → stop and point the operator at
the `linode-team` MCP setup in `.claude/README.md`.

**Test-suite dependencies** (drive the pytest run, Step 7). Verify they're installed —
`python3 -c "import pytest, paramiko, requests"` (backend tests need these three; `playwright` is
still installed for the shared suite but backend tests never import it). If not, install per the
suite's README:

```bash
pip install -r tests/regression_tests/requirements.txt
```

**No Playwright MCP needed.** Unlike `/ui-regression-tests`, this skill drives no browser — all
probing is SSH + HTTP. If the Playwright MCP happens to be connected, ignore it.

**Detect the mode.** `.documentation/<app>/STATE.md` exists → **pipeline mode**: read it (it carries
the working branch — `GH_USER`/`BRANCH` for the deploy) and proceed — nothing to ask. Otherwise →
**standalone mode**: gather the operator-supplied inputs in **one message** — the scenarios (unless
`--scenarios` was given; see Step 2) and, only if the operator wants **unmerged code** tested rather
than published `main`, the fork/branch to deploy from.

**The app's deploy material.** Confirm `apps/linode-marketplace-<app>/` and
`deployment_scripts/linode-marketplace-<app>/` (`<app>-deploy.sh` + `test-vars.sh`) exist — these
are what Step 3 copies to the box and runs.

**Scope gate — is the app actually headless?** These are service tests, not browser tests. Confirm
the app's **primary surface is not a web UI** before proceeding. In pipeline mode, read it from
`architecture_decisions.md` (no nginx-proxied browsable UI / auth is API-key or protocol-level, not
a login form); in standalone mode, from the app's playbook (`roles/<app>` — no web vhost serving an
app UI) or by asking the operator. If the app's main surface **is** a browsable web UI (a login
form, an admin console, a dashboard) → **STOP** and point the operator at `/ui-regression-tests`.
Borderline apps that ship a *thin* admin console but whose product is the data/service plane
(e.g. a DB with a small management page) can be split: browser bits go to `/ui-regression-tests`,
the data/service plane is this skill's — say so explicitly and test only the backend surface here.

### Step 2 — Establish the scenarios

The baseline (service-active, plus port-listening when there's a port worth asserting on) is always
covered. Everything beyond that comes from, in priority order:

1. **`--scenarios` was given** → use it as the scenario list. Still skim the artifacts below for
   context that changes how you test (auth model, bind address, a known data endpoint).
2. **Pipeline mode** (artifacts exist under `.documentation/<app>/`) → derive candidates from them.
   Earlier phases already describe how a real user exercises this service; don't re-invent that:
   - `e2e_testing.md` — the smoke tests `/app-deploy` ran (service up, port reachable, a client
     round-trip). These are often **already backend-shaped** — lift them directly.
   - `manual_install.md` — the Phase 2c smoke tests and the by-hand exercise of the service's
     primary function (the psql query, the `redis-cli` session, the `wg show`).
   - `architecture_decisions.md` / `vetting.md` — auth model, bind address / firewall posture,
     expected data endpoints.

   Distill these into a short numbered list of **service-testable** scenarios, each with the
   artifact it came from. **Present the list to the operator and ask one question:** write the
   regression tests from these scenarios, or adjust/replace them? Wait for the answer.
3. **Standalone mode with no `--scenarios`** → ask the operator for a plain-language description of
   what to test beyond the baseline (folded into Step 1's single standalone-inputs message).

Record the confirmed scenario list — it drives the probe (Step 5), the generated test functions
(Step 6), and the artifact (Step 9).

### Step 3 — Deploy the app (the skill's own box)

Deploy exactly the way **CI (the GitHub Actions workflow) does it**: a plain empty box, then the
app's own deploy script. This mirrors a real deploy end to end and sidesteps StackScript UDF
quirks (e.g. an `add_ons` UDF declared `manyOf="…, none"` with `default="none"` is rejected when
`"none"` is passed via `stackscript_data` — the deploy-script path never hits that validation).
Deploy a **fresh** box — fresh matters, because tests run on freshly deployed VMs and any one-time
first-run state (an init token, a seeded admin, an unseal key) must still be present to capture.

1. **Create an empty box**: `mcp__linode-team__create_linode` with the image CI uses (typically
   `linode/ubuntu24.04` — take it from `STATE.md` / the deploy material if it differs), a **generated
   `root_pass`**, and the **operator's SSH pubkey** via `authorized_keys`. **No `stackscript_id`** —
   the box is bare Ubuntu; the deploy script does the provisioning. Record box id + IP.
2. **Wait for SSH**: `get_linode` until `running`, then poll
   `ssh -o StrictHostKeyChecking=accept-new root@<ip>` (the box is brand-new, so plain `ssh` would
   die at the host-key prompt) until it answers.
3. **Copy the deploy material** from `deployment_scripts/linode-marketplace-<app>/` to the box:
   `test-vars.sh` (the canonical UDF list with CI defaults) and `<app>-deploy.sh` (clones the repo +
   runs the playbook). `scp` both to `/root/`.
4. **Run the deploy** in one shell so the UDF env from `test-vars.sh` carries into the script, and
   run it **detached** so the SSH call can return (the script logs to `/var/log/stackscript.log`
   itself via its own `exec` redirect):
   ```bash
   ssh … root@<ip> 'cd /root && chmod +x <app>-deploy.sh && \
     nohup bash -c "source /root/test-vars.sh && bash /root/<app>-deploy.sh" \
     >/var/log/deploy-wrapper.log 2>&1 & echo started'
   ```
   - `test-vars.sh` supplies the identity/config UDFs with CI defaults (`USER_NAME`, `DISABLE_ROOT`,
     …) and generates any empty secrets; you don't build a payload by hand.
   - To test **unmerged code** (a working branch/fork), `export GH_USER=<fork> BRANCH=<branch>`
     before the script — it reads them (default is `akamai-compute-marketplace` / `main`). In
     pipeline mode both come from `STATE.md`. The branch must be **pushed** — if it isn't, STOP and
     ask the operator to push (Claude never pushes).
5. **Monitor to completion — bounded**: tail `/var/log/stackscript.log` until the Ansible
   `PLAY RECAP` / `Installation Complete`; confirm the service came up. **Bound: 30 minutes from
   boot** — not done by then → treat it as a failed deploy (point 6).
6. **If the deploy fails → STOP. Full stop — do not debug or fix anything.** This skill is about
   regression tests; a broken deployment is not its problem to solve. Report what failed (the
   relevant `stackscript.log` lines, box id) and hand it to the operator. The same rule applies to
   the Step 7b redeploy.

Boxes this skill creates are throwaway test boxes, but **tearing them down is the operator's manual
step** — the skill never deletes Linodes (team standing rule).

### Step 4 — SSH into VM: get endpoint(s) and credentials

> **If anything here errors** (an SSH host-key complaint, or a missing MOTD/credentials key) →
> **check `troubleshooting.md` first** — each of these has a documented fix.

Every Marketplace app writes into `/etc/motd` at deploy time. For a headless app, the useful keys
are whichever of these exist:
- `App URL:` — present when the app exposes an HTTP API (use as `base_url` for `http_session`).
  Many pure services (a firewalled DB) have **no** `App URL` — that's expected; the service is
  reached over SSH, not a URL.
- `Credentials File:` — the absolute path to the app credentials file on the VM.

#### 4a — Read the MOTD

```bash
ssh -o StrictHostKeyChecking=accept-new root@<ip> 'cat /etc/motd'
```

(`accept-new` is required on every skill-deployed box: it's a first contact, and non-interactive
`ssh` would otherwise fail at the host-key prompt.)

- `App URL` value (if present) → this is `base_url` for HTTP checks.
- `Credentials File` value → this is `credentials_file_path`.

**Edge case:** neither key present → some apps write deploy info to the interactive shell welcome
instead; see `troubleshooting.md`, or ask the operator.

#### 4b — Read the credentials file

```bash
ssh -o StrictHostKeyChecking=accept-new root@<ip> 'cat <credentials_file_path>'
```

- Save the **exact key names** — use them verbatim as `app_credentials["..."]` in tests. Exact key
  names matter because `app_credentials` parses the file as-is at runtime.
- Identify which key is the login/user, which is the password/token, which is an API key.
- Use the actual values to authenticate during probing (Step 5) — but never write them into a test
  file, the chat beyond what the tool output already shows, or the Step 9 artifact.

**Edge cases:**
- Credentials file not found or empty → check the deploy log; if genuinely absent, ask the operator
  where the app's credentials live.
- Service has no auth (e.g. a loopback-only cache with no password) → skip the credential-based
  checks; the baseline is service-active + port-state only.
- Credentials file **repeats a key name** across service accounts → `app_credentials` keeps only the
  last; see the dedicated `troubleshooting.md` entry (targeted re-parse in the app conftest).

### Step 5 — Probe the live service

Real command output from a live service produces tests that actually work. Guessed output produces
tests that fail on first run. Probe over SSH (`ssh -o StrictHostKeyChecking=accept-new root@<ip>
'<cmd>'`) and, where an API exists, over HTTP.

> **If a probe errors** (`command not found` for the client, a port that won't connect, a TLS error
> on the API, a service that's active but not yet ready) → **check `troubleshooting.md` first** —
> each has a documented fix.

**Liveness baseline — always.**
- **Service active:** `systemctl is-active <unit>` (find the real unit name — it isn't always
  `<app>`; check `systemctl list-units | grep -i <app>` or the playbook). Capture the exact unit
  name and the `active` output.
- **Port state:** `ss -tlnp` / `ss -ulnp` — record which port the service binds and **on what
  address** (`127.0.0.1:<port>` = loopback-only; `0.0.0.0:<port>` / `*:<port>` = all interfaces).
  Cross-check the firewall (`iptables -S` / the app's UFW rules / the Linode Cloud Firewall) so the
  test asserts the *intended* posture. A loopback bind is correct for a firewalled datastore —
  assert it as such, don't treat it as a failure.

**Functional probe — per confirmed scenario + the archetype table.** Run the app's own client on
the box and capture exact output:
- DB: `PGPASSWORD=... psql -h 127.0.0.1 -U <user> -c 'SELECT 1'` / `mysql -u <user> -p... -e 'SELECT 1'`;
  pgvector: `CREATE EXTENSION IF NOT EXISTS vector; SELECT '[1,2,3]'::vector;`.
- Cache: `redis-cli -a <pass> --no-auth-warning ping` → capture `PONG`; a `SET`/`GET` roundtrip.
  (`--no-auth-warning` keeps the auth notice off stderr so it can't muddy the assertion.)
- Broker: `curl -sk http://127.0.0.1:8222/healthz`, `/varz`; a `nats pub`/`sub` roundtrip if the CLI
  is present.
- VPN/network: `wg show` / `ip -brief link`; confirm the listening UDP/TCP port; `stat -c '%a' <keyfile>`
  for the expected perms (e.g. `600`).
- API app: hit `App URL` + the documented paths (`/api/version`, `/v1/.well-known/ready`, a metrics
  path). If the port is loopback-only, `curl` it over SSH; if public, note it can be hit directly.

**Capture, for every probe:** the exact command, the exact stdout you'll assert on (or a stable
substring), the exit code, and the vantage (SSH vs. direct HTTP). These become the service-object
methods and the test assertions verbatim.

> **Probing can mutate the box.** Creating a bucket/collection, initializing/unsealing, or consuming
> a first-run token changes the instance — that's expected (you're capturing it), and it's exactly
> why the final test run happens on a fresh redeploy (Step 7), never on this box.

### Step 6 — Generate and save test files

See `${CLAUDE_SKILL_DIR}/templates/test-file-templates.md` for exact code templates.

**Shared infra — add once, reuse forever.** The first backend app needs the shared plumbing; later
apps reuse it untouched.
- `tests/regression_tests/services/__init__.py` → **create it the first time** (empty). This is the
  package-level init that makes `regression_tests.services.*` importable — the exact counterpart of
  the existing `pages/__init__.py` / `utils/__init__.py`. Without it the SOM imports fail. **If it
  already exists, leave it.**
- `tests/regression_tests/utils/ssh.py` → add `run_remote_command(host, user, password, command)`
  returning `(stdout, stderr, exit_code)`, built on the existing `ssh_connection`. **If it already
  exists, reuse it — do not redefine.**
- `tests/regression_tests/conftest.py` → add the `remote_exec` fixture (a callable bound to
  `ssh_credentials`) and the `http_session` fixture (`requests.Session`, `verify=False`). **If they
  already exist, reuse them — do not redefine.** These are shared, tracked files the UI suite also
  uses; touching them is a deliberate, reviewed footprint (it's on the manual-review checklist).

**Files to create (per app):**

```
tests/regression_tests/services/{pkg}/__init__.py            (empty; skip if the folder already exists)
tests/regression_tests/services/{pkg}/{pkg}_service.py       (client/CLI/API actions — no assertions)
tests/regression_tests/apps/linode-marketplace-{app}/conftest.py    (credentials_file_path; base_url only if the app has an HTTP API)
tests/regression_tests/apps/linode-marketplace-{app}/test_scenarios.py
```

**When the app dir already exists (overlap / borderline apps).** Some apps already have a
`apps/linode-marketplace-{app}/` from a *browser* run (`/ui-regression-tests`) — e.g.
`nats-single-node`, which ships a thin monitoring page and already has browser tests + a `pages/nats`
package. In that case **do not overwrite** `conftest.py` or `test_scenarios.py` — merge:
- `test_scenarios.py` → **append** the backend `def test_...` functions and their `import`s; leave the
  existing browser tests intact.
- `conftest.py` → add only the fixtures that aren't already there (e.g. `credentials_file_path` if
  missing). **Never redefine an existing `base_url`** — reuse the one the browser suite defined.
- `{pkg}` → reuse the app's existing `pages/{pkg}` name (per the derivation rule) so the backend
  service objects sit under the same package identity as the page objects.

**Code rules** — these keep tests independent, readable, and consistent with the rest of the suite:

- **First test = app up and working** — the first `def test_...` in the file verifies the app
  responds (health/liveness for a service; entrypoint runs for a library/CLI), before any
  port/scenario test. See "Baseline tests" above.
- **No test classes** — plain `def test_...` functions only.
- **No `try`/`finally` in tests** — never. If a test creates throwaway state, use a unique name and
  leave cleanup to the (disposable) box, or clean up with a plain trailing call; don't wrap the body
  in `try`/`finally`. It hides failures and adds control-flow noise.
- **No assertions in service classes** — service objects hold client/CLI/API *actions* and return
  raw results (stdout, response, parsed value). Assertions belong in test functions, exactly like
  "no assertions in page classes" in the UI suite.
- **Fresh connection per action** — service methods run each command through `remote_exec` (which
  opens/closes its own SSH per call); don't stash a long-lived session on the object. Independent
  calls keep tests from bleeding state into each other.
- **Descriptive failure messages** — every `assert` takes a message (`assert code == 0, "redis unit
  not active"`). Without it, a CI failure gives no context.
- **Comment style matches the UI suite** — a single concise `# Verifies that …` line right after the
  `def`, saying what the test checks. Not multi-line prose, not a running commentary.
- **Assert on stable output** — match an exact token (`PONG`, `active`) or a stable substring
  (`'"status":"ok"'`, `# TYPE`), never volatile fields (timestamps, uptimes, connection counts).
- **Random names for test-created data** — give any object a test creates (collection, bucket, key,
  row, DB) a unique per-run name (e.g. a `uuid` suffix). This keeps a create/round-trip test passing
  on a fresh **or** reused box and keeps the suite re-runnable (it also tends to make the suite
  idempotent-only — see Step 7b).
- **Absolute imports** — `regression_tests.services.{pkg}.{file}` (no relative imports).
- **Slow operations** — pass a generous `timeout` to `remote_exec` / `http_session` for heavy work
  (an LLM generate, a large index build); default SSH/HTTP timeouts are for quick commands.
- **Never import Playwright** in a backend test or service object — backend tests don't use the
  browser and must not request `context`/`browser`.

### Step 7 — Run the tests (iterate, then verify on a fresh redeploy)

The suite's global `ssh_credentials` fixture reads `LINODE_IPV4` and `LINODE_ROOT_PASS` from the
environment (`tests/regression_tests/conftest.py`) — the skill's own values from Step 3 (the box IP
and the generated root pass), passed inline (run from the repo root):

```bash
LINODE_IPV4=<box-ip> LINODE_ROOT_PASS=<generated-root-pass> \
  python3 -m pytest tests/regression_tests/apps/linode-marketplace-{app}/ -v
```

**7a — Iterate on the exploration box.** Run the suite against the Step 3 box to shake out unit-name,
port, command-output, and auth errors cheaply. Expect one class of "failure" that is **not a bug**:
tests that consume one-time state (an init token, a first-run seed) or that create-then-assert
content fail here because the probe already consumed/created that state. Don't weaken those tests to
pass on a used box — that's what 7b is for.
- On any failure, **first check `troubleshooting.md`** for the symptom; if listed, apply the
  documented fix. Otherwise inspect the error, fix the command/expected-output/port assertion,
  re-run.
- Still failing (excluding consumed-state failures) after 2 attempts → stop and ask the operator.

**7b — Fresh redeploy = the real pass condition.**
1. Redeploy fresh via the Linode MCP: repeat Step 3 mechanics — new empty box, the **same
   `test-vars.sh`** (so `USER_NAME` is unchanged: the app conftest's `credentials_file_path` bakes in
   `/home/<user>/`), same `<app>-deploy.sh` (same `GH_USER`/`BRANCH`), **newly generated** root pass,
   operator pubkey. Monitor to completion (same 30-minute bound).
2. Point the tests at the new box (only the inline `LINODE_IPV4`/`LINODE_ROOT_PASS` change; the
   conftest derives everything else from the host) and run the **full suite**.
3. **Pass condition: everything green on the fresh box, including any one-time-state tests.** If
   something fails, fix the tests, then **redeploy fresh again and rerun** — a box whose one-time
   state was already consumed is spent; never "just rerun" on it. Same 2-attempt escalation.

> **Idempotent-only suites.** If the app's every check is idempotent (`is-active`, `PING`,
> `SELECT 1`, a read-only API probe — no init-token consumption, no create-then-assert), 7a and 7b
> converge and a fresh box isn't strictly required to re-prove. Still do one clean fresh-deploy run
> for parity with the rest of the pipeline and record that box id.

Record which box the final green run happened on (box id) — it goes in the Step 9 artifact.

### Step 8 — Record new failure modes

Keep `troubleshooting.md` alive so future runs don't re-solve the same problems. After the run,
append a new entry **only if all four gates pass** — otherwise add nothing:

1. **Confirmed** — the test actually passed *after* your fix. Never record a guess.
2. **Novel** — the symptom isn't already covered (you read it in Step 7, so you know).
3. **Recurring-likely** — a class of failure that could hit another headless app (unit-name
   discovery, firewall/bind posture, client-not-on-box, readiness races, TLS on data endpoints,
   auth-format quirks, credential parsing), not a one-off app-specific tweak.
4. **Structured** — follow the existing `Symptom → Cause → Fix` shape, reference the relevant
   fixture/file/template, and end with provenance: `(confirmed on <app>, YYYY-MM)`.

**When a documented fix doesn't work:** that attempt counts against the Step 7 bound, and the entry
may be stale — say so in the hard-stop report so the operator can judge it. Do **not** silently edit
or delete existing entries; the file is append-only for Claude, and pruning stale entries is an
operator decision in PR review.

`troubleshooting.md` is a **tracked team file**: an edit lands in the diff and a human reviews it in
the PR before it's trusted. When in doubt, leave it out; a wrong entry actively misleads the next run.

### Step 9 — Record the `backend_testing.md` artifact

Record what this run did so the next person (or run) has context — this skill's per-app artifact, the
parallel of `e2e_testing.md` / `ui_testing.md`. Append a dated section to
`.documentation/<app>/backend_testing.md` (per-app working notes live under `.documentation/<app>/`
and are gitignored — never synced) using the artifact template in
`${CLAUDE_SKILL_DIR}/templates/test-file-templates.md`. Get the date with `date '+%Y-%m-%d'`; create
the file if it doesn't exist, append a new section if it does.

Capture: scope/scenarios (and where they came from — artifacts vs. operator), what was
**discovered** (unit name, bind address + firewall posture, client commands, API endpoints), files
**created** (service objects + test functions, and whether the shared `remote_exec`/`http_session`
infra was added this run), the **boxes deployed** (ids only) with which one carried the final green
run, and any **issues** worth noting (slow ops, readiness races, new troubleshooting entries).

**No sensitive data — this is a hard rule.** Never write credentials, passwords, tokens, or
credential-file contents into the artifact, and **do not include the base URL / API endpoint.**
Credential *key names*, unit names, port numbers, and box *ids* are fine; secret values and the
reachable URL are not.

**Pipeline mode:** also update `STATE.md` — mark the backend-tests phase done, record the suite
paths (`services/{pkg}/`, `apps/linode-marketplace-{app}/`) and the final green box id, and set
`next_step: /app-pr`.

## Output
- `tests/regression_tests/services/{pkg}/` — SOM service classes (this command owns them).
- `tests/regression_tests/apps/linode-marketplace-{app}/` — `conftest.py` + `test_scenarios.py`.
- `tests/regression_tests/services/__init__.py` + `utils/ssh.py` + global `conftest.py` —
  `services/__init__.py` / `run_remote_command` / `remote_exec` / `http_session` added the first time
  (reused, not redefined, thereafter).
- A full-suite green run against a **fresh deploy** (exploration + verification boxes left up;
  teardown is the operator's manual step).
- `troubleshooting.md` — appended only when a novel, confirmed failure mode was hit.
- `.documentation/<app>/backend_testing.md` — the per-app backend-testing artifact (no sensitive data).
- `STATE.md` updated (pipeline mode): backend-tests phase done, `next_step: /app-pr`.

## STOP — manual review (checkpoint)
Before relying on the generated tests, the operator verifies:
- [ ] Every command / expected output / port / API response traces to a real probe of the live service — no guessed output.
- [ ] The scenario list was confirmed by the operator (from artifacts or their own input), and every confirmed scenario has a test.
- [ ] Every box was skill-deployed via the Linode MCP with generated secrets.
- [ ] The port-state assertion reflects the **intended firewall posture** — a loopback-only bind is asserted as correct, not flagged as a failure.
- [ ] Functional checks run on the correct vantage (client on the box for loopback/firewalled services; direct HTTP only for genuinely public endpoints).
- [ ] `{pkg}` reuses an existing `services/` **or** `pages/` folder name when one exists (no duplicate/divergent package for the same app).
- [ ] `services/__init__.py` exists (package-level init — the counterpart of `pages/__init__.py`); SOM imports resolve.
- [ ] For an app that already had a browser suite, `test_scenarios.py` / `conftest.py` were **merged, not overwritten** (existing browser tests + `base_url` intact).
- [ ] The **full suite passed on a fresh redeploy** (or, for idempotent-only suites, one clean fresh-deploy run).
- [ ] Shared infra reused, not redefined: `remote_exec` / `http_session` / `run_remote_command` / `services/__init__.py` added once globally; no per-app copies; global browser fixtures untouched.
- [ ] No service object contains an assertion; no backend test imports Playwright or requests `context`/`browser`.
- [ ] Any new `troubleshooting.md` entry passed all four gates (confirmed, novel, recurring-likely, structured).
- [ ] The `backend_testing.md` artifact contains no credential values and no base URL / endpoint; test boxes torn down manually when done.

**Next:** `/app-pr` — the operator reviews the generated tests + any `troubleshooting.md` diff and
commits them on the working branch.
