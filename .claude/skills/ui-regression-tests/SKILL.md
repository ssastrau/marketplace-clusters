---
description: UI tests — generate Playwright + Pytest UI regression tests for a Marketplace app that has a web UI (headless / API-only apps are out of scope). Deploys its own box via the Linode MCP, explores the live app with a real browser, generates Page Object Model test files matching the suite's conventions, then verifies the full suite on a fresh redeploy. Runs in pipeline mode (after /validate-config) or standalone (operator supplies the inputs). User-invoked only.
disable-model-invocation: true
arguments: [app, --scenarios, --stackscript]
---

# UI Regression Tests (Generate Live-Explored Browser Tests)

Generate Playwright + Pytest tests for a Linode Marketplace app by exploring a **live deployed
app** first, then producing real-locator Page Object Model (POM) test files that match the existing
`tests/regression_tests/` suite conventions — and proving them with a **full suite pass on a fresh
redeploy** (because exploration consumes any one-time first-run state, a used box can never be the
pass condition).

It deploys its own boxes from the app's StackScript, so it only needs the app's playbook + deploy
script to exist (and, for unpublished apps, the working branch to be pushed).

**Scope: apps with a web UI.** These are *browser* tests, so headless / API-only apps (databases,
VPNs, message brokers, exporter-style agents) are out of scope — backend testing will be its own
skill. The skill checks this up front (Step 1) and stops if the app has no UI.

## Usage
```
/ui-regression-tests <app> [--scenarios "<free text>"] [--stackscript <id>]
```
Parse `--scenarios` and `--stackscript` from `$ARGUMENTS`; `$app` is the first positional.

## Arguments
- `<app>`: the full Marketplace directory suffix under `apps/`, **hyphenated**, exactly as deployed
  (e.g. `apache-airflow`, `hashicorp-nomad`). Used for
  `tests/regression_tests/apps/linode-marketplace-<app>/`.
- `--scenarios "<free text>"`: optional plain-language description of what to test beyond
  the startup/login baseline. When omitted, scenarios come from the artifact discovery in Step 2
  (pipeline mode) or the operator (standalone mode).
- `--stackscript <id>`: optional StackScript id to deploy from — mainly for standalone runs where
  no `STATE.md` records one.

## Two modes (detected at Step 1, from whether `STATE.md` exists)

- **Pipeline mode** — `.documentation/<app>/STATE.md` exists (run after `/validate-config`):
  StackScript, branch, and scenarios are all discovered from `STATE.md` and the phase artifacts,
  with a single operator confirmation of the scenario list.
- **Standalone mode** — no `STATE.md`: the operator supplies the scenarios (via `--scenarios`,
  or asked) and, if the skill can't find one itself, the StackScript (via `--stackscript`, or
  asked). Collect every missing input in **one message** — don't drip-feed questions.

Either way the access model is identical: the skill deploys its own boxes.

## Hard stops — no indefinite loops (non-negotiable)

When anything is **unclear**, an **input is missing**, or a **bounded retry is exhausted**, the
skill STOPS: it reports where it is, what it has, and exactly what it needs — then waits for the
operator. It never guesses past a gap, never improvises a workaround, and never keeps retrying
"one more time." The hard stops, with their bounds:

| Condition | Bound |
|---|---|
| Playwright MCP or Linode MCP not available | stop immediately (Step 1) |
| App has no web UI (headless / API-only) | stop at Step 1 — browser tests don't apply |
| Scenarios missing or too vague to test from | stop and ask once (Steps 1–2); unanswered → stay stopped |
| StackScript can't be located by any lookup | stop and ask (Step 3) |
| Working branch not pushed | stop; operator pushes (Step 3) |
| Deploy (or redeploy) fails | stop immediately — **zero** debug/fix attempts (Steps 3, 7b) |
| Deploy still not finished while monitoring | **30 min** from boot, then treat as a failed deploy (Step 3) |
| App unreachable / selector or credential not observable | stop and ask (Steps 4–5) |
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
- **Skill-driven box reads** (MOTD, credentials file) go over key-based `ssh root@<ip>` — the
  operator's pubkey is on the box because the skill put it there.
- **App login credentials** — read from the box's credentials file over SSH (Step 4), used only to
  drive the live exploration and referenced in tests by **key name** via the `app_credentials`
  fixture. Never hardcoded into a test, never written to the artifact.
- Don't echo the generated root password or app credential **values** into chat text or artifacts
  beyond what tool calls inherently show.

## Grounding contract (non-negotiable)
Tests are written from what the live app actually shows — never from memory or guesswork:
- Every selector, page title, and login flow comes from a real `browser_snapshot` of the deployed
  app (Step 5). A guessed locator is a test that fails on first run.
- Scenarios presented to the operator in Step 2 cite the artifact they came from
  (`e2e_testing.md`, `manual_install.md`, …) — never invented from memory of the app.
- The pass condition is empirical: the full suite green against a **fresh deploy** (Step 7), not
  against the box the exploration already mutated.
- If the live app can't be reached, or a required selector / credential can't be observed, **STOP
  and ask the operator.** Do not fabricate a test against an imagined UI.

## Flow overview

```
1. Prerequisites        →  MCPs connected? App has a web UI (else STOP)? Detect mode (STATE.md?); standalone → collect inputs
2. Establish scenarios  →  --scenarios, or pipeline artifacts + operator confirms, or operator-provided (standalone)
3. Deploy the app       →  StackScript deploy via Linode MCP (generated root pass + operator pubkey), monitor
                           deploy fails → STOP and report; fixing the deployment is the operator's job
4. SSH into VM          →  Read /etc/motd (base_url) + credentials file (login keys, if the app has a login)
5. Explore with browser →  Navigate live app, capture real selectors (this consumes any first-run wizard)
6. Generate test files  →  POM page classes + test_scenarios.py + conftest.py
7. Run tests            →  Iterate on the exploration box, then REDEPLOY fresh and pass the full suite clean
8. Record failure modes →  Append confirmed, novel issues to troubleshooting.md
9. Record artifact      →  Summarize the run in .documentation/<app>/ui_testing.md; pipeline mode: update STATE.md
```

## On any error — check `troubleshooting.md` first (standing rule)

**This applies at _every_ step, not just the test run** — the entries span SSH reads, browser
exploration, and the pytest run. The moment any command fails, **read `troubleshooting.md` and
look for the matching symptom before improvising a fix.** If the symptom is listed, apply the
documented fix; only if it isn't do you diagnose from scratch. New, confirmed, novel failures get
appended back per Step 8.

## Test suite conventions

Understanding these upfront avoids generating code that doesn't fit the project.

**Placeholders used throughout this skill:**
- `{app}` — see `<app>` above (hyphenated directory suffix).
- `{pkg}` — the Python package name under `pages/`. **Derived automatically:** if
  `tests/regression_tests/pages/` already contains a folder for this app, reuse it (match by
  inspection — e.g. `apache-airflow` → existing `airflow`, `uptimekuma` → existing `uptime_kuma`);
  otherwise use `{app}` with hyphens replaced by underscores (`hashicorp-nomad` →
  `hashicorp_nomad`). Must be a valid Python identifier.
- `{App}` — PascalCase class prefix for page objects (e.g. `Airflow`, `ArangoDB`).
- `{Feature}` — PascalCase name of a page/scenario (e.g. `Dashboard`, `Collections`).

```
tests/regression_tests/
├── conftest.py                          # global fixtures — do NOT redefine these
├── pages/
│   └── {pkg}/
│       ├── __init__.py
│       ├── {pkg}_login_page.py          # only when the app has a login
│       └── {pkg}_{feature}_page.py
└── apps/
    └── linode-marketplace-{app}/
        ├── conftest.py                  # app-specific: credentials_file_path, base_url
        └── test_scenarios.py
```

**Baseline tests.** A **startup** test is always generated. A **login** test is generated **only
when the app actually has a login** (a login form / native auth observed in Step 5). Public,
no-auth apps get no login test and no login page object — don't invent one to fill the template.

**Global fixtures already defined — never redefine in app conftest:**
- `ssh_credentials` — reads `LINODE_IPV4`, `LINODE_ROOT_USER`, `LINODE_ROOT_PASS` from env
- `app_credentials` — SSHes into VM, parses credentials file as `Key: Value` pairs
- `context` — a fresh Playwright **`Page`** per test (it yields a `Page` despite the name). Pass it
  wherever a page is expected, e.g. `{App}LoginPage(context)`.
- `http_credentials` — returns `None` by default, which is correct for **most apps** — leave it
  alone. Only override it in the app conftest in the rare case the app sits behind HTTP Basic Auth
  (e.g. htpasswd); then the global `context` fixture passes it to `new_context(http_credentials=...)`.
  See the "HTTP Basic Auth" template. Apps with a normal in-page login form do **not** use this.

## Process

### Step 1 — Prerequisites

**Playwright MCP** (drives the live exploration, Step 5). Verify the tools are available
(`browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`).

If **not available** → stop and tell the operator:

> Playwright MCP is not connected. Add it to Claude Code, then restart this chat:
> ```bash
> claude mcp add playwright -- npx @playwright/mcp@latest --headless --ignore-https-errors
> ```
> Both flags are required: `--headless` (no browser window pops up during exploration; matches how
> the suite runs Chromium) and `--ignore-https-errors` (test deploys sit on
> `*.ip.linodeusercontent.com` with self-signed certs — without it every `browser_navigate` fails).

Do not fall back to Python scripts or any other method. Stop and wait.

**Test-suite dependencies** (drive the pytest run, Step 7 — separate from the MCP: the suite uses
its own Python Playwright). Verify they're installed —
`python3 -c "import pytest, playwright, paramiko, pytest_html"` (the global conftest imports all
four at collection time); if not, install them per the suite's README:

```bash
pip install -r tests/regression_tests/requirements.txt
playwright install chromium
```

**Linode MCP.** Verify `mcp__linode-team__*` tools are available (`create_linode`,
`list_stackscripts`, …) — this skill deploys its own boxes through them. If not available → stop
and point the operator at the `linode-team` MCP setup in `.claude/README.md`.

**Detect the mode.** `.documentation/<app>/STATE.md` exists → **pipeline mode**: read it (it
carries the team StackScript id `stackscript_deploy` and the working branch) and proceed —
nothing to ask. Otherwise → **standalone mode**: gather the operator-supplied inputs in **one
message** — the scenarios (unless `--scenarios` was given; see Step 2) and, if Step 3's
StackScript lookup will have nothing to go on (no `--stackscript`, no obvious match), which
StackScript to deploy from.

**The app's deploy material.** Confirm `apps/linode-marketplace-<app>/` and
`deployment_scripts/linode-marketplace-<app>/` (`<app>-deploy.sh` + `test-vars.sh`) exist —
needed for the UDF payload and, if necessary, to create the StackScript.

**Scope gate — does the app have a web UI?** These are browser tests, so confirm the app serves a
web interface before deploying a box for it. In pipeline mode, read it from
`architecture_decisions.md` (nginx reverse proxy + a browsable `App URL` / auth model); in
standalone mode, from the app's playbook (`roles/<app>` nginx vhost) or by asking the operator.
Headless / API-only apps (databases, VPNs, message brokers, exporter-style agents) have nothing
to browser-test → **STOP**..

### Step 2 — Establish the scenarios

The baseline (startup, plus login when the app has one) is always covered. Everything beyond
that comes from, in priority order:

1. **`--scenarios` was given** → use it as the scenario list. Still skim the artifacts below for
   context that changes how you test (auth model, a known first-run page).
2. **Pipeline mode** (artifacts exist under `.documentation/<app>/`) → derive candidates from
   them. Earlier phases already describe how a real user exercises this app; don't re-invent that:
   - `e2e_testing.md` — the smoke tests `/app-deploy` ran (front page, login, installer 4xx).
   - `manual_install.md` — the Phase 2c smoke tests, the observed login flow, and the user-level
     exercise of the app's primary function captured during the by-hand install.
   - `architecture_decisions.md` / `vetting.md` — auth model, expected first-run/setup behavior.

   Distill these into a short numbered list of **browser-testable** scenarios (skip pure infra
   checks like "DB port not public" — those belong to `e2e_testing.md`, not a UI suite), each with
   the artifact it came from. **Present the list to the operator and ask one question:** write the
   regression tests from these scenarios, or adjust/replace them? Wait for the answer.
3. **Standalone mode with no `--scenarios`** → ask the operator for a plain-language description
   of what to test beyond the baseline (folded into Step 1's single standalone-inputs message).

Record the confirmed scenario list — it drives the exploration (Step 5), the generated test
functions (Step 6), and the artifact (Step 9).

### Step 3 — Deploy the app (the skill's own box)

Deploy a **fresh** box for exploration — fresh matters, because tests run on freshly deployed VMs
and any one-time first-run state must still be present to capture. Reuse `/app-deploy`'s deploy
mechanics:

1. **Locate the StackScript**, in priority order:
   - `--stackscript <id>` when given (typical standalone run);
   - `STATE.md` `stackscript_deploy` id (pipeline mode — the team StackScript `/app-deploy` created);
   - else `mcp__linode-team__list_stackscripts` and match by app name — before adopting a match,
     read its script body (in the response) and confirm any `# BEGIN CI-GH` block targets the
     intended fork+branch; a stale branch deploys the wrong code, so a mismatch = not found;
   - else create one via `mcp__linode-team__create_stackscript` from
     `deployment_scripts/linode-marketplace-<app>/<app>-deploy.sh`, setting `GH_USER`/`BRANCH` in
     the `# BEGIN CI-GH` block to the operator's fork + working branch (per `/app-deploy`). The
     branch must be **pushed** — if it isn't, STOP and ask the operator to push (Claude never
     pushes).
2. **Build the UDF payload from `deployment_scripts/linode-marketplace-<app>/test-vars.sh`** —
   that file is the app's canonical UDF list with its CI defaults. Use its defaults as-is for
   identity/config fields (`USER_NAME`, `DISABLE_ROOT`, domain fields, …); for the fields it
   leaves empty because they're secrets (passwords, tokens), **generate** values. Cross-check
   against the deploy script's `#<UDF …>` declarations that no required field is missing.
3. **Deploy**: `mcp__linode-team__create_linode` with the StackScript + payload, Ubuntu 24.04,
   a **generated `root_pass`**, and the **operator's SSH pubkey** via `authorized_keys`. Record
   box id + IP.
4. **Monitor to completion — bounded**: `get_linode` until `running`, then SSH
   (`-o StrictHostKeyChecking=accept-new` — the box is brand-new, so plain `ssh` would die at the
   host-key prompt) and tail `/var/log/stackscript.log` until the Ansible play recap; confirm the
   app responds. **Bound: 30 minutes from boot** — not done by then → treat it as a failed deploy
   (point 5).
5. **If the deploy fails → STOP. Full stop — do not debug or fix anything.** This skill is about
   regression tests; a broken deployment is not its problem to solve. Report what failed (the
   relevant `stackscript.log` lines, box id) and hand it to the operator — fixing the deployment
   is theirs to handle. The same rule applies to the Step 7b redeploy.

Boxes this skill creates are throwaway test boxes, but **tearing them down is the operator's
manual step** — the skill never deletes Linodes (team standing rule).

### Step 4 — SSH into VM: get base URL and credentials

> **If anything here errors** (an SSH host-key complaint, or `App URL`/`Credentials File` missing
> from `/etc/motd`) → **check `troubleshooting.md` first** — each of these has a documented fix.

Every Marketplace app writes two things into `/etc/motd` at deploy time:
- `App URL:` — the full URL where the app is running → use this as `base_url` in tests
- `Credentials File:` — the absolute path to the app credentials file on the VM

Both are `Key: Value` formatted, so two plain key-based SSH reads are all that's needed:

#### 4a — Read the MOTD

```bash
ssh -o StrictHostKeyChecking=accept-new root@<ip> 'cat /etc/motd'
```

(`accept-new` is required on every skill-deployed box: it's a first contact, and non-interactive
`ssh` would otherwise fail at the host-key prompt.)

Example `/etc/motd` contents (the banner line varies per app — current branding is
`Akamai Connected Cloud <App> Quick Deploy App`; **only the `App URL:` and `Credentials File:` keys
matter for parsing**):

```
Akamai Connected Cloud <App> Quick Deploy App
App URL: https://172-233-219-65.ip.linodeusercontent.com:3000/ui/panel
Credentials File: /home/admin/.credentials
Documentation: https://www.linode.com/marketplace/apps/...
```

- `App URL` value → this is `base_url`
- `Credentials File` value → this is `credentials_file_path`

**Edge case:** `App URL` or `Credentials File` not present → see `troubleshooting.md`
(some apps write deploy info to the interactive shell welcome instead), or ask the operator.

#### 4b — Read the credentials file

```bash
ssh -o StrictHostKeyChecking=accept-new root@<ip> 'cat <credentials_file_path>'
```

Credentials file format:

```
App Admin Email: admin@example.com
App Admin Password: secret123
```

- Save the **exact key names** — use them verbatim as `app_credentials["..."]` in tests.
  Exact key names matter because `app_credentials` parses the file as-is at runtime.
- Identify which key is the login username and which is the password.
- Use the actual values to log in during exploration (Step 5) — but never write them into a test
  file, the chat beyond what the tool output already shows, or the Step 9 artifact.

**Edge cases:**
- Credentials file not found or empty → check the deploy log; if it's genuinely absent, ask the
  operator where the app's credentials live
- App has no login (public app) → skip the credentials read, the login page object, and the login
  test — the baseline is startup only

### Step 5 — Explore the app with Playwright MCP

Real selectors from a live app produce tests that actually work. Guessed selectors produce
tests that fail on first run.

> **If navigation errors** (`net::ERR_CERT_AUTHORITY_INVALID` / `SEC_ERROR_*` SSL errors, or every
> request returning `401 Unauthorized`) → **check `troubleshooting.md` first** — both have a
> documented fix (self-signed cert handling; HTTP Basic Auth via `http_credentials`).

> **Exploration mutates the box.** Completing a first-run wizard or creating content changes the
> instance permanently — that's expected (you're capturing it), and it's exactly why the final
> test run happens on a fresh redeploy (Step 7), never on this box.

**Landing page**
- `browser_navigate` → `base_url`
- `browser_snapshot` → record:
  - Exact page `<title>` for `to_have_title()`
  - Login form element selectors (inputs, labels, submit button) — if the app has a login
  - Any stable visible landmark elements

**First-run configuration page detection.** Some apps require a one-time configuration the first
time you open them — creating an admin account, naming a resource, setting a domain, finishing an
install step, etc. It is **not always labelled "setup" or "wizard"**; it's simply a page (or short
sequence of pages) you complete once. After it's done and you log in again it disappears forever and
the app goes straight to its normal dashboard. Because tests run on freshly deployed VMs, this
first-run state IS what CI hits — so it must be captured during exploration and driven by the tests.

If the app shows a first-run configuration page (often right after the first login):
- Record all input selectors and button locators for every step
- Complete each step to advance, recording as you go (**you only get one chance per box** — after
  this, only a redeploy brings the wizard back)
- Note what confirms completion (redirect to dashboard, created entity visible, etc.)
- Generate a page object for it like any other feature page, named for **what it does** rather than
  generically — e.g. `{pkg}_setup_page.py`, `{pkg}_onboarding_page.py`,
  `{pkg}_create_station_page.py`.

**Login flow** (when the app has one)
- Fill username → fill password → click submit
- `browser_snapshot` post-login → record a stable element that confirms successful login
  (heading, nav item, unique dashboard element)

**Per-scenario pages.** For each scenario confirmed in Step 2 beyond the baseline:
- Navigate to the relevant section
- `browser_snapshot` → record selectors for elements the scenario interacts with

**Locator priority.** Prefer stable, semantic selectors. Dynamic class names (e.g. `css-1a2b3c`)
break when the app updates — avoid them entirely.

```
#id  →  [aria-label]  →  get_by_role(name=)  →  [name=]  →  XPath (last resort)
```

### Step 6 — Generate and save test files

See `${CLAUDE_SKILL_DIR}/templates/test-file-templates.md` for exact code templates to use for each file type.

**Files to create:**

```
tests/regression_tests/pages/{pkg}/__init__.py          (empty; skip files that already exist when reusing a pages folder)
tests/regression_tests/pages/{pkg}/{pkg}_login_page.py        (only when the app has a login)
tests/regression_tests/pages/{pkg}/{pkg}_{feature}_page.py    (one per feature/scenario)
tests/regression_tests/apps/linode-marketplace-{app}/conftest.py    (no __init__.py — app dirs don't use one)
tests/regression_tests/apps/linode-marketplace-{app}/test_scenarios.py
```

A first-run configuration page (see Step 5) is just another `{pkg}_{feature}_page.py` — name it
for what it does. Use the generic "Page class" template for it; there's no separate template.

**Code rules** — these keep tests independent, readable, and consistent with the rest of the suite:

- **No test classes** — plain `def test_...` functions only. Classes add indirection with no benefit here.
- **Re-login per test** — each test that needs auth must log in fresh. Shared sessions cause
  flaky failures that are hard to diagnose because one test's state bleeds into another.
- **Descriptive failure messages** — every `expect()` call takes a failure message as second
  argument. Without it, a failed assertion in CI gives no context about what was being checked.
- **No assertions in page classes** — page classes contain locators and actions only. Assertions
  belong in test functions so the intent of each test is visible in one place.
- **Absolute imports** — `regression_tests.pages.{pkg}.{file}` (no relative imports), consistent
  with the rest of the suite.
- **Slow operations** — add `timeout=180000` (Playwright timeouts are in **milliseconds**;
  180000 ms = 3 min) for AI responses, heavy processing, or anything that regularly takes more
  than a few seconds.

### Step 7 — Run the tests (iterate, then verify on a fresh redeploy)

The suite's global `ssh_credentials` fixture reads `LINODE_IPV4` and `LINODE_ROOT_PASS` from the
environment (`tests/regression_tests/conftest.py`). Both are the skill's own values from Step 3 —
the box IP and the root password the skill generated — passed inline (run from the repo root):

```bash
LINODE_IPV4=<box-ip> LINODE_ROOT_PASS=<generated-root-pass> \
  python3 -m pytest tests/regression_tests/apps/linode-marketplace-{app}/ -v
```

**7a — Iterate on the exploration box.** Run the suite against the Step 3 box to shake out locator,
title, and timing errors cheaply. Expect one class of "failure" that is **not a bug**: tests that
drive the first-run wizard (or assert single-instance content) fail here because exploration
already consumed that state. Don't weaken those tests to pass on a used box — that's what 7b is for.
- On any failure, **first check `troubleshooting.md`** for the symptom; if listed, apply the
  documented fix. Otherwise inspect the error, fix selectors/titles/locators, re-run.
- Still failing (excluding consumed-state failures) after 2 attempts → stop and ask the operator.

**7b — Fresh redeploy = the real pass condition.** One-time setup wizards mean tests can't run
twice on the same instance — so the suite is only proven against a pristine box:
1. Redeploy fresh via the Linode MCP: repeat Step 3 mechanics — same StackScript, the **same
   `test-vars.sh` identity/config values** (`USER_NAME` especially: the app conftest's
   `credentials_file_path` bakes in `/home/<user>/`), **newly generated** secrets + root pass,
   operator pubkey. Monitor to completion (same 30-minute bound).
2. Point the tests at the new box (the conftest derives `base_url` from the host, so only the
   inline `LINODE_IPV4`/`LINODE_ROOT_PASS` values change) and run the **full suite**.
3. **Pass condition: everything green on the fresh box, including first-run tests.** If something
   fails, fix the tests, then **redeploy fresh again and rerun** — a box whose wizard has been
   consumed (by a test run or otherwise) is spent; never "just rerun" on it. Same 2-attempt
   escalation to the operator.

Record which box the final green run happened on (box id) — it goes in the Step 9 artifact.

### Step 8 — Record new failure modes

Keep `troubleshooting.md` alive so future runs don't re-solve the same problems. After
the run, append a new entry **only if all four gates pass** — otherwise add nothing:

1. **Confirmed** — the test actually passed *after* your fix. Never record a guess or an unverified
   "this might be it."
2. **Novel** — the symptom isn't already covered in `troubleshooting.md` (you read it in
   Step 7, so you already know).
3. **Recurring-likely** — it's a class of failure that could hit another app (cert/auth/wizard/SSH/
   credential-parsing/locator patterns), not a one-off typo or an app-specific selector tweak.
4. **Structured** — follow the existing `Symptom → Cause → Fix` shape, reference the relevant
   fixture/file/template so the fix is actionable, and end with provenance:
   `(confirmed on <app>, YYYY-MM)`.

**When a documented fix doesn't work:** that attempt counts against the Step 7 bound, and the
entry may be stale — say so in the hard-stop report so the operator can judge it. Do **not**
silently edit or delete existing entries; the file is append-only for Claude, and pruning stale
entries is an operator decision in PR review.

`troubleshooting.md` is a **tracked team file**: an edit lands in the diff and a human
reviews it in the PR before it's trusted — that review is the quality gate. When in doubt, leave it
out; a wrong entry actively misleads the next run.

### Step 9 — Record the `ui_testing.md` artifact

Record what this run did so the next person (or run) has context — this is the skill's per-app
artifact, the parallel of `e2e_testing.md` / `validation_findings.md`. Append a dated section to
`.documentation/<app>/ui_testing.md` (per-app working notes live under `.documentation/<app>/`
and are gitignored — never synced) using the artifact template in
`${CLAUDE_SKILL_DIR}/templates/test-file-templates.md`. Get the date with `date '+%Y-%m-%d'`; create
the file if it doesn't exist, append a new section if it does.

Capture: scope/scenarios (and where they came from — artifacts vs. operator), what was
**discovered** (titles, login flow or its absence, first-run page), files **created** (page
objects + test functions), the **boxes deployed** (ids only) with which one carried the final
green run, and any **issues** worth noting (slow ops, flaky areas, new troubleshooting entries
added in Step 8).

**No sensitive data — this is a hard rule.** Never write credentials, passwords, tokens, or
credential-file contents into the artifact, and **do not include the base URL.** Credential *key
names* and box *ids* are fine; secret values are not.

**Pipeline mode:** also update `STATE.md` — mark the UI-tests phase done, record the suite paths
(`pages/{pkg}/`, `apps/linode-marketplace-{app}/`) and the final green box id, and set
`next_step: /app-pr`.

## Output
- `tests/regression_tests/pages/{pkg}/` — POM page classes (this command owns them).
- `tests/regression_tests/apps/linode-marketplace-{app}/` — `conftest.py` + `test_scenarios.py`.
- A full-suite green run against a **fresh deploy** (the exploration box and the verification box
  are left up; teardown is the operator's manual step).
- `troubleshooting.md` — appended only when a novel, confirmed failure mode was hit.
- `.documentation/<app>/ui_testing.md` — the per-app UI-testing artifact (no sensitive data).
- `STATE.md` updated (pipeline mode): UI-tests phase done, `next_step: /app-pr`.

## STOP — manual review (checkpoint)
Before relying on the generated tests, the operator verifies:
- [ ] Every selector / title / login flow traces to a real `browser_snapshot` of the live app — no guessed locators.
- [ ] The scenario list was confirmed by the operator (from artifacts or their own input), and every confirmed scenario has a test.
- [ ] Every box was skill-deployed via the Linode MCP with generated secrets.
- [ ] A login test exists **only if** the app has a login; no invented login flow for public apps.
- [ ] `{pkg}` reuses the existing `pages/` folder when one exists (no duplicate package for the same app).
- [ ] The **full suite passed on a fresh redeploy** (not the exploration box), including any first-run/wizard tests.
- [ ] Global fixtures (`context`, `app_credentials`, `http_credentials`) are reused, not redefined in the app conftest.
- [ ] Any new `troubleshooting.md` entry passed all four gates (confirmed, novel, recurring-likely, structured).
- [ ] The `ui_testing.md` artifact contains no credential values and no base URL; test boxes torn down manually when done.

**Next:** `/app-pr` — the operator reviews the generated tests + any `troubleshooting.md` diff and
commits them on the working branch.
