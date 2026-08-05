---
description: Addon pipeline (compressed) — build a new add-on task file for apps/linode_helpers/roles/addons/ end-to-end (manual install → ansibilize → wire UDFs → deploy-test on pilot apps → PR prep), after /app-vet rendered an `addon` verdict. User-invoked only.
disable-model-invocation: true
arguments: [addon, --repo]
---

# Addon: Build (The Addon Mini-Pipeline)

The whole pipeline for an **add-on** — the addon-shaped counterpart of phases 2–6, compressed
into one skill because the artifact is one task file in
`apps/linode_helpers/roles/addons/tasks/`, not a 96th app directory. Run after `/app-vet`
rendered an `addon` verdict (read `.documentation/<addon>/vetting.md` if it exists; if the
operator decided `addon` without vetting, that decision note is the input instead).

An add-on is an optional agent that enhances *other* deployed apps: enabled per-deployment via
the `add_ons` `manyOf` UDF, installed by the consuming app's `roles/post` via
`import_role: addons`, and dispatched through the `{ name, file }` include loop in
`apps/linode_helpers/roles/addons/tasks/main.yml`.

## Usage
```
/addon-build <addon> [--repo <git-url>] [--region us-east] [--type g6-standard-2]
```
`<addon>` is the snake_case name that will appear in the `add_ons` list and UDF `manyOf=`
(e.g. `node_exporter` — task *files* use hyphens, `node-exporter.yml`; match both conventions
to the existing members).

## Grounding contract (non-negotiable)
Same as the app pipeline: every decision cites a **doc URL**, a **repo `file:line` + commit
SHA**, or a **command + output + box id**. Inventory the existing add-ons live
(`ls apps/linode_helpers/roles/addons/tasks/`) — never from memory. Upstream install scripts are
**parsed, never executed**. If a fact cannot be grounded, record it as an OPEN QUESTION and STOP.

Standing rules: **Claude never pushes to GitHub** (operator reviews + pushes every commit);
**no destructive commands without permission**; back up before risky edits.

## Process

### Stage 1 — Manual install on a test box
1. Initialize `.documentation/addon-<addon>/STATE.md` from
   `${CLAUDE_SKILL_DIR}/templates/state.md`. Shallow-clone `--repo` into `.reference/<repo>`
   (record the SHA). Read the upstream install docs for the **agent** form (binary release,
   package, or single container) — per the `/app-vet` rubric an add-on is never a compose stack.
2. Deploy a fresh Ubuntu 24.04 test box via `mcp__linode-team__create_linode` — **generated
   `root_pass` AND the operator's SSH pubkey** (same provisioning pattern as
   `/app-manual-install` Phase 2a). Record box id/ip in `STATE.md`.
3. Install the agent **by hand**, capturing every command + output into
   `.documentation/addon-<addon>/manual_install.md`: download/verify the binary (or package),
   dedicated system user if non-root, config file, systemd unit, start, and the addon-specific
   health check (e.g. metrics endpoint curl on loopback). If the addon targets a host service
   (the mysqld_exporter shape), install that service first and capture the wiring (limited-grant
   DB user, credentials file).
4. **STOP — checkpoint:** operator SSHes in, confirms the agent is `active` and its health check
   passes, and that `manual_install.md` is complete enough to ansibilize from.

### Stage 2 — Ansibilize into a single task file
5. Pick reference members: rank the existing addon task files by date-added
   (`git log --diff-filter=A --format=%cs -- apps/linode_helpers/roles/addons/tasks/<file> | tail -1`,
   newest first) and read the **newest 2** in full as primary refs; cite `file:line` for every
   borrowed pattern. The documented anatomy (verify against those files, don't assume):
   - Version discovery from the upstream releases API (`uri` module) where applicable.
   - `get_url` / `unarchive` → binary to `/usr/local/bin/` (never `curl | bash`).
   - Dedicated system user via the shared `promuser.yml`-style import when the agent shouldn't
     run as root.
   - systemd unit shipped from `addons/files/`, config from `addons/templates/`; enable + start
     via one `systemd` task (`daemon_reload: true`).
   - `block`/`rescue` graceful skip when the addon depends on an optional host service (the
     pattern at the tail of `addons/tasks/mysqld-exporter.yml` — debug message, play continues).
   - If post-install interactive config is needed (API tokens, endpoints): a
     `templates/<addon>.sh.j2` snippet inserted via
     `lineinfile: insertafter: '^# BEGIN ADDONS'` into `/etc/profile.d/addons.sh`, self-removing
     on completion — the pattern documented in `apps/linode_helpers/README.md`
     §"Post Add-on installation steps".
6. Write `apps/linode_helpers/roles/addons/tasks/<addon>.yml` from `manual_install.md` (each
   captured command → a declarative module task), add the `{ name: "<addon>", file: "<addon>.yml" }`
   entry to the include loop in `addons/tasks/main.yml`, and ship any `files/` / `templates/`
   artifacts. Lint with the repo's committed checks (same scripts `/app-ansibilize` uses):
   `tests/static_code_analysis/yaml_configs/check_yaml_configs.sh` +
   `tests/static_code_analysis/ansible_playbooks/check_ansible_playbooks.sh` against
   `apps/linode_helpers`, and `tests/static_code_analysis/shell_scripts/check_shell_scripts.sh`
   against any touched `deployment_scripts/` dirs.
7. **STOP — checkpoint:** inline review of the task file against the anatomy above + lint clean.

### Stage 3 — Wire the UDFs (rollout decision)
8. Find the current consumers: `grep -rl 'name="add_ons"' deployment_scripts/`. Adding the addon
   to an app = appending `<addon>` to that script's `manyOf=` list (the `add_ons` group_vars
   plumbing and the `roles/post` import already exist in consuming apps — verify per pilot app,
   citing the file:line, rather than assuming).
9. **STOP — rollout decision (operator's call):** pilot **1–2 apps** vs. all consumers. Default
   to a pilot; rolling the UDF change across ~30 deployment scripts is a separate, conscious
   follow-up (possibly its own PR). Pick pilots whose stack matches the addon's target (e.g. a
   MySQL-backed app for a DB-adjacent addon; any consumer for a host-level agent). Record the
   choice in `STATE.md`.

### Stage 4 — Deploy-test on the pilot apps
10. For each pilot app, run a fresh StackScript deploy with the addon selected in the UDF
    payload, reusing `/app-deploy`'s mechanics verbatim: branch pushed by the operator first,
    team StackScript with `GH_USER`/`BRANCH` pointing at the fork+branch (`update_stackscript`
    for revisions; `DEBUG="yes"` on iteration boxes so the work dir survives failure), monitor
    `/var/log/stackscript.log`, and the two-tier fix loop (fix-on-VM → mirror locally → **STOP
    for operator push** → fresh redeploy). The pass condition is a clean fresh deploy with no
    VM-side edits.
11. Addon-specific smoke, recorded in `.documentation/addon-<addon>/e2e_testing.md`: agent
    service `active`; health/metrics endpoint responds **on loopback**; **no new publicly
    reachable port** (an add-on must not widen the app's firewall surface — anything it exposes
    stays on `127.0.0.1` or goes through the consuming app's existing authenticated proxy, per
    `CLAUDE.md` §6); the consuming app's own smoke tests still pass; and a control deploy
    (addon **not** selected) is unaffected.
12. **STOP — checkpoint:** both the addon smoke and the host app's smoke are green on a clean
    fresh deploy.

### Stage 5 — PR prep
13. Update the docs: add the addon to the Add-ons row / supported list in
    `apps/linode_helpers/README.md` (and its post-install configuration steps if it has a
    profile.d prompt). Draft `.documentation/addon-<addon>/pr_description.md`: what the addon
    does, the manual-install evidence, pilot deploy-test results, the rollout scope (pilots now,
    rest later?), and any OPEN QUESTIONS consciously deferred.
14. Update `STATE.md`: all stages checked, boxes + stackscript ids recorded, `next_step: operator
    opens the PR`. Claude never opens or pushes the PR.

## Output
- `apps/linode_helpers/roles/addons/tasks/<addon>.yml` (+ `files/` / `templates/` artifacts) and
  the `main.yml` loop entry.
- Pilot `deployment_scripts/.../<app>-deploy.sh` `manyOf=` updates.
- `.documentation/addon-<addon>/` — `STATE.md`, `manual_install.md`, `e2e_testing.md`,
  `pr_description.md`.
- Updated `apps/linode_helpers/README.md`.

## STOP — manual review (final checkpoint)
- [ ] Task file follows the addon anatomy; every borrowed pattern cites `file:line`.
- [ ] Clean fresh pilot deploys with the addon on **and** a control deploy with it off.
- [ ] No new publicly reachable port; anything listening is loopback-only or behind existing auth.
- [ ] Rollout scope (pilot vs. all consumers) was an explicit operator decision, recorded.
- [ ] Operator reviewed + pushed every commit; operator opens the PR.

**Next:** operator opens the PR vs `develop`.
