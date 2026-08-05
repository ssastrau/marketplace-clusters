---
description: Phase 2 — install a marketplace app by hand on a fresh Linode following architecture_decisions.md + repo standards, capturing every command into manual_install.md. The validated box becomes the reference for the Ansible port. User-invoked only.
disable-model-invocation: true
arguments: [app]
---

# App: Manual Install (Phase 2 — Build It By Hand)

Perform the install **by hand** on a fresh Linode, following the approved
`architecture_decisions.md` and this repo's standards, capturing every command into
`manual_install.md`. This is the empirical phase that finds the breaking changes a legacy
StackScript hides and resolves the OPEN QUESTIONS from Phase 1. The validated box becomes the
reference the Ansible port (`/app-ansibilize`) is built against.

Shared by both backport and new-app paths.

## When to run
Reads `.documentation/<app>/STATE.md`. Run this once a `STATE.md` (with research/architecture
notes) exists for the app. That usually comes from `/backport-start` or `/newapp-start` — **but
if the operator did their own up-front R&D and hand-wrote `architecture_decisions.md` +
`STATE.md`, run directly from those.** The skill needs grounded decisions to install against; it
does not care which produced them.

## Usage
```
/app-manual-install <app> [--region us-east] [--type g6-standard-2]
```

## Grounding contract
This phase *is* the empirical grounding. Every step in `manual_install.md` must be a real command
run on the box with its observed output. Resolve every OPEN QUESTION from
`architecture_decisions.md` here, by observation — never by guessing. If a doc claim turns out
false on the box, the box wins; update `architecture_decisions.md` with the empirical correction +
citation.

## Process

### Phase 2a — Fresh box
1. Read `STATE.md` and `architecture_decisions.md`. Deploy a **fresh** Ubuntu 24.04 Linode via
   `mcp__linode-team__create_linode` (clean image, not the legacy box). **Set a generated
   `root_pass` AND add the operator's SSH pubkey via `authorized_keys`** (ideally both). Surface
   the root password to the operator. Record box id / ip / rDNS in `STATE.md`.
2. SSH in as root and confirm a clean baseline.

### Phase 2b — Install by hand, capturing every command
3. Work through the install following `architecture_decisions.md` + `CLAUDE.md` standards, **as
   root** (drop to a sudo user or `www-data` only for the specific steps an app actually requires
   it). **Paste every command and its observed output into `manual_install.md` as you go** (one
   command per line, with the result), in this order:
   - Base packages / runtime / dependencies (current upstream versions).
   - The app itself via the chosen install method (Docker/Compose, package repo, source, or binary).
   - **systemd** unit(s) for every long-running process.
   - **nginx** reverse proxy if the app uses a non-standard port; bind the app/API to `127.0.0.1`
     where possible.
   - **certbot** SSL with HTTP→HTTPS redirect (use a real hostname / rDNS).
   - **Generated credentials** — admin password, DB creds, API keys generated on the box, written
     to `/home/<user>/.credentials` (mode 0600). No defaults.
   - **Eliminate the installer / setup wizard** (`CLAUDE.md` §7/§7a): pre-bake config, drive any
     CLI installer non-interactively, delete/deny the installer endpoint, and smoke-test that it
     returns 4xx — not the wizard.
   - **Outer auth layer** if the public URL is itself an admin surface (`CLAUDE.md` §"Hard Rules").
     CMS-style browse-then-login apps don't need it.
   - **UFW** (22, 80, 443, + only the app ports users actually need), **fail2ban**, sudo user.

4. **Upstream install scripts — parse, never run (critical).** If upstream ships an install script
   (`curl | bash`, `install.sh`, `setup.sh`, …), **do not execute it.** Open it from the
   `.reference/<repo>` clone, read it line-by-line, and run only the *applicable* underlying
   commands by hand — capturing each into `manual_install.md`. The reason: install scripts change
   silently upstream and break deploys, and the marketplace playbook must be declarative. Capturing
   the discrete commands here is **exactly what lets `/app-ansibilize` convert each one to a
   declarative Ansible task.** Note in `manual_install.md` which script line each command came from
   (`install.sh:NN @ <sha>`).

> SSH hardening is **not** part of the manual session — you are working as root the whole time;
> disabling root/password SSH here would only lock you out of debugging. SSH hardening lives in
> the Ansible port (`securessh` in `roles/common`, gated on `disable_root`), not here.

### Phase 2c — Validate the box
5. Smoke-test on the box and record results in `manual_install.md`: front page 200 over HTTPS,
   HTTP→HTTPS 301, installer endpoint 4xx, admin login works, DB port not publicly reachable,
   services `active`, no EOL/insecure banners.
6. Resolve every OPEN QUESTION from `architecture_decisions.md` with an empirical answer; update
   that file where the box contradicted the docs.
7. Leave the box **up** as the Ansibilize reference. Update `STATE.md`: mark `manual-install` done,
   record box id/ip + credentials path, set `next_step: /app-ansibilize`.

## Output
- `.documentation/<app>/manual_install.md` — the by-hand walkthrough, every command + output
  (this command owns it), with upstream-script line provenance where applicable.
- `architecture_decisions.md` updated with empirical corrections.
- `STATE.md` updated; reference box left running.

## STOP — manual review (checkpoint)
The operator personally verifies before proceeding:
- [ ] **SSH into the box and do a real UI login + smoke test** — the app works end-to-end.
- [ ] Installer/wizard is gone (returns 4xx, not setup HTML).
- [ ] Credentials are generated (no defaults) and in `/home/<user>/.credentials`.
- [ ] `manual_install.md` is complete enough to Ansibilize from (every install-script command captured).

**Next:** `/app-ansibilize`
