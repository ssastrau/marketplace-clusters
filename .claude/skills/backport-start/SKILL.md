---
description: Phase 1 (backport) — deploy a legacy marketplace StackScript app to a live Linode, analyze it against current standards, and produce a cited architecture_decisions.md + initialize STATE.md. User-invoked only.
disable-model-invocation: true
arguments: [app]
---

# Backport: Start (Research + Analyze the Legacy App)

Front-end for a **backport** — taking an older StackScript-era marketplace app and
re-architecting it as a modern Ansible playbook. Deploys the *existing* legacy app to a live
Linode, analyzes it against current standards, and produces the grounded
`architecture_decisions.md` every later phase builds on. Initializes the per-app `STATE.md`.

This is the first command in the pipeline. For a brand-new app (no legacy StackScript), use
`/newapp-start` instead — the downstream phases are identical.

Optionally preceded by `/app-vet` (Phase 0 triage). If `.documentation/<app>/vetting.md` exists,
read it first and:
- carry its **verdict + taxonomy bucket** into `STATE.md` instead of re-deriving the classification
  — Phase 2's reference-app selection starts from the vetted bucket;
- treat its **OPEN QUESTIONS as first-class research targets** for Phase 2 — resolve each one with a
  grounded citation as a numbered `Dn` in `architecture_decisions.md`, or, if it can only be settled
  on a live box, re-flag it as an OPEN QUESTION for `/app-manual-install`. Do not silently drop a
  vetting OQ.

## Usage
```
/backport-start <app> --stackscript <id> --repo <git-url> [--docs <url>] [--region us-east] [--type g6-standard-2]
```
Parse `--stackscript`, `--repo`, `--docs`, `--region`, `--type` from `$ARGUMENTS`; `$app` is the
first positional. Any remaining free-text prose is **operator steering** (see Arguments) — never
discard it.

## Arguments
- `<app>`: short app name, lowercase (e.g. `joomla`, `nomad`). Used for
  `apps/linode-marketplace-<app>/` and `.documentation/<app>/`.
- `--stackscript <id>`: **required.** The legacy StackScript ID to introspect and deploy. The
  command reads its `user_defined_fields` rather than you hand-writing UDFs.
- `--repo <git-url>`: **required.** The upstream source repository to clone and analyze against
  current standards (Phase 2) — not the legacy script's pinned version.
- `--docs <url>`: optional pointer to the official documentation root (otherwise discovered via search).
- `--region`, `--type`: optional placement/size. Default a small Ubuntu 24.04 box.
- **Operator steering (free text):** any prose after the flags is operator instruction — custom
  questions, hard constraints, preferred versions, or answers to / overrides of vetting OPEN
  QUESTIONS. Honor every item: fold it into the Phase 2 analysis and record the resolution as a
  cited `Dn` in `architecture_decisions.md` (or an OPEN QUESTION if it can only be settled
  empirically on the box). **Never answer a steering question from memory** — ground it with a doc
  URL / repo `file:line`+SHA / empirical observation like any other decision.

## Grounding contract (non-negotiable)
Every decision must cite a source — a **doc URL**, a **repo `file:line` + commit SHA**, or an
**empirical observation** (command + output + box ID). Pull sources in explicitly; never reason
from memory:
- Official docs → `WebFetch` / `WebSearch`, capture the exact URL.
- Upstream source → `git clone` into `.reference/<repo>` (gitignored) and read the *actual*
  install scripts, config templates, and defaults. **Record the commit SHA** so every
  `file:line @ SHA` citation is reproducible. Also consult the repo's own `ansible/` clone for
  module params.
- Live behavior → SSH onto the box and observe (rendered configs, `systemctl` state, listening
  ports, HTTP responses).

**If a fact cannot be grounded, record it as an OPEN QUESTION and STOP for the operator. Do not guess.**

## Process

### Phase 1a — Introspect the legacy StackScript
1. Read the legacy StackScript via `mcp__linode-team__get_stackscript` (id from `--stackscript`).
   Capture its `user_defined_fields`, target images, and script body.
2. Build a **representative UDF payload** from the field schema: fill required fields with
   realistic values and **generate any secrets** (passwords, tokens) rather than placeholders.
   Record the payload in `STATE.md` (redact secret *values* — store only field names + that they
   were generated).

### Phase 1b — Deploy the legacy app for analysis
3. Deploy a box with `mcp__linode-team__create_linode` using the legacy StackScript + your
   payload (Ubuntu 24.04, `--type`/`--region` or defaults). **Set a generated `root_pass` AND add
   the operator's SSH pubkey via `authorized_keys`** (ideally both, so the operator can get in
   either way). Write the root password into the run's credentials notes and surface it to the
   operator. Record box id / ip / rDNS in `STATE.md`.
4. Wait for the deploy to finish (`get_linode` until `running`; poll `/var/log/stackscript.log`
   over SSH). Confirm the legacy app is actually up (HTTP response, service status). This box is
   the **analysis reference**, not the final artifact.

### Phase 2 — Analyze against current standards
5. `git clone` the `--repo` URL into `.reference/<repo>` (gitignored working dir). Record the
   commit SHA in `STATE.md`. Read the real install method, config templates, and version/dependency
   requirements from the **current** upstream release — not the legacy script's pinned version.
6. Read official docs (install guide, security/hardening guide, production deployment notes) via
   `WebFetch`, starting from `--docs` when provided (otherwise discover the doc root via search).
7. Compare and reconcile three things: (a) what the legacy StackScript does, (b) what current
   upstream docs recommend, (c) what `CLAUDE.md` mandates + how the closest existing apps structure
   things. **To pick those reference apps**, follow `.claude/shared/reference-apps.md`: classify this
   app's archetype (install method, web/proxy, auth model, GPU?/DB?/PHP?) → match one bucket → rank
   that bucket's members by date-added (`git log --diff-filter=A --format=%cs -- apps/linode-marketplace-<m> | tail -1`,
   newest first) → read the **newest 2–3 members' actual files** and cite `file:line` for any pattern
   borrowed.
8. Re-architect for current standards — do **not** replicate the legacy script. Apply: systemd
   services, nginx reverse proxy for non-standard ports, certbot SSL + HTTP→HTTPS, generated
   credentials (no defaults), no open installer/setup wizard, API on loopback. **Auth layering —
   exactly ONE layer, never an unauthenticated console:** native login **OR** nginx basic auth, not
   both. Prefer the app's **native login** whenever it has one (enforced). Use **basic auth only as
   the fallback** when there's no enforceable native login (so the console isn't open — e.g. Nomad's
   no-ACL UI). Layer **both only transiently** when a post-install step needs protection before native
   auth is live (e.g. HaltDOS's emailed 6-digit code), then remove the basic-auth layer. No standing
   two-layer. See `CLAUDE.md` §"Backporting Legacy Apps" + §"Hard Rules for Backports".

### Phase 3 — Write `architecture_decisions.md` + init `STATE.md`
9. Write `.documentation/<app>/architecture_decisions.md` as a numbered decision log
   (`D1`, `D2`, …). Each `Dn` states the decision, the alternatives considered, and a **source
   citation** (doc URL / repo `file:line`+SHA / empirical observation on the box). Flag anything
   ungroundable as `OPEN QUESTION`.
10. Initialize `.documentation/<app>/STATE.md` from the bundled template
   `${CLAUDE_SKILL_DIR}/templates/state.md`: set `type: backport`, the branch, the legacy
   stackscript id, the analysis box id/ip, the upstream clone path + SHA, mark `research/analyze`
   done, set `next_step: /app-manual-install`.

## Output
- `.documentation/<app>/architecture_decisions.md` — cited decision log (this command owns it).
- `.documentation/<app>/STATE.md` — initialized handoff file.
- A short operator summary: box ip + root password location, the decision count, and any OPEN
  QUESTIONS to resolve before proceeding.

## STOP — manual review (checkpoint)
Before the next command, the operator verifies:
- [ ] `architecture_decisions.md` is sound, current, and every `Dn` carries a real citation.
- [ ] Every **vetting OPEN QUESTION** and every **operator-steering item** is resolved with a
      citation as a `Dn`, or consciously deferred to manual install — none dropped.
- [ ] All OPEN QUESTIONS are resolved (or consciously deferred).
- [ ] The chosen install method matches current upstream, not the stale legacy version.

**Next:** `/app-manual-install`
