# Marketplace App Workflow — Claude Code Skills

A chain of **user-invoked skills** that encode the team's end-to-end process for bringing apps
into the Linode Marketplace — both **backports** (legacy StackScript → modern Ansible playbook)
and **new apps** (R&D → playbook). Each skill does one phase, hands off through a per-app state
file, and **stops at a manual-review checkpoint** so a human verifies the work before the next
phase runs.

These live in `.claude/skills/` and are shared by the whole team. They live in the private
`marketplace-claude-skills` repo and are symlinked into each `marketplace-apps` checkout as
`.claude/` (see that repo's top-level `README.md` for setup) — so the tooling is shared across the
team without ever entering the public marketplace repo.

> **Skills and commands.** The pipeline ships as skills (`.claude/skills/<name>/SKILL.md`). Each
> carries `disable-model-invocation: true` so it is **only ever run when you type `/<name>`** —
> Claude never auto-triggers a phase. Skill names come from the directory, so they are flat +
> hyphenated (`/app-deploy`, not `/app:deploy`). One utility ships as a command
> (`/setup-cloud-manager-dev`); skills and commands work side by side.

## Order of operations

```
TRIAGE (optional):  /app-vet <app> [--repo <git-url>]  ──▶ vetting.md: verdict routes ↓
                      new-app / already-exists(STOP) / not-deployable(STOP) / not-suitable(STOP)
                      └─ addon ──▶ /addon-build <addon> --repo <git-url>   (mini-pipeline, see below)

BACKPORT:  /backport-start <app> --stackscript <id> --repo <git-url> ─┐
NEW APP:   /newapp-start   <app> --repo <git-url>                  ───┤   each →
                                                                      ▼   architecture_decisions.md + STATE.md
            /app-manual-install <app>      ──STOP: SSH + UI login test the box──▶
            /app-ansibilize     <app>      ──STOP: inline review + local lint──▶
            /app-deploy         <app>      ──STOP: clean fresh deploy + smoke tests──▶
            /validate-config <app> --instance <ip>   ──STOP: directive matrix──▶
            ├─ web-UI app ──▶ /ui-regression-tests      <app>  ──STOP: full UI suite green on a fresh redeploy──┐
            └─ headless app ─▶ /backend-regression-tests <app>  ──STOP: full backend suite green on a fresh redeploy─┤
            /app-pr             <app>      ──▶ README (written last) + PR vs develop
            /app-docs           <app>      ──▶ public Linode Docs guide (as needed; outside core pipeline)
```

`/backport-start` and `/newapp-start` are the two entry points — pick one per app. Everything from
`/app-manual-install` onward is identical for both. **You can also start at `/app-manual-install`**
if you did your own R&D and hand-wrote `architecture_decisions.md` + `STATE.md` — the pipeline only
needs grounded decisions to install against, not a particular skill that produced them.

**Phase 0 — `/app-vet` (optional triage).** Before spending Phase 1 on a candidate, `/app-vet`
renders a grounded verdict: `new-app`, `addon`, `already-exists`, `not-deployable-as-named`
(library/SDK/SaaS-only — names the deployable sibling product), or `not-suitable`. Grounded in
live `ls apps/` + the live addons inventory, never memory. The `:start` skills read
`vetting.md` when it exists instead of re-deriving the classification.

**Addon branch — `/addon-build`.** When the verdict is `addon` (an agent that enhances other
deployments — exporter/collector shape, no web UI of its own), the artifact is one task file in
`apps/linode_helpers/roles/addons/tasks/`, not an app directory. `/addon-build` compresses the
pipeline accordingly: manual install → ansibilize (single task file + `main.yml` loop entry) →
wire `manyOf=` UDFs into pilot apps (rollout is an explicit operator decision) → fresh
deploy-test of the pilots → PR prep. Same standing rules and STOP checkpoints; state in
`.documentation/addon-<name>/STATE.md`.

**Docs step — `/app-docs`.** Outside the core pipeline: it drafts the customer-facing
[Linode Docs](https://github.com/linode/docs) marketplace guide (`index.md`) for an app. Run it as
the last step when an app is new or its public guide needs updating. It reads the app's code and
`.documentation/<app>/` notes for ground truth and **drafts only** — the operator previews, edits,
and opens the docs PR.

**UI-tests step — `/ui-regression-tests`.** Generates the app's browser regression suite: it
deploys its own box from the app's StackScript via the Linode MCP (generated secrets), explores
the live app with a real browser, writes Playwright + Pytest POM tests into
`tests/regression_tests/`, and proves them with a full-suite pass on a fresh redeploy (one-time
setup wizards mean tests can't run twice on the same box). It also runs standalone, with the
operator supplying scenarios. Deploy failures are hard stops — this skill never fixes the
playbook. Applies to apps with a web UI only.

**Backend-tests step — `/backend-regression-tests`.** The **complement** of the UI skill for
**headless / API-only** apps (databases, caches, message brokers, VPNs, vector stores, LLM/exporter
APIs) — whatever `/ui-regression-tests` STOPs on. Same frame (self-deploys its own box, generated
secrets, hard-stop on deploy failure, fresh-redeploy pass condition, standalone-capable), but it
probes the **live service over SSH** (the app's own client/CLI) and its **HTTP API** where one
exists instead of driving a browser, then writes Pytest **Service Object Model** tests into
`tests/regression_tests/`. The two skills are a **fork at phase 6** — the pipeline routes to exactly
one based on whether the app's primary surface is a web UI. Adds shared `remote_exec` / `http_session`
plumbing to the suite the first time it runs; reuses it thereafter.

| Phase | Skill / command | Owns artifact | Checkpoint before next |
|---|---|---|---|
| 0 Triage *(optional)* | `/app-vet` | `vetting.md` | verdict cited; routes to next command |
| 1 Research / analyze | `/backport-start` or `/newapp-start` | `architecture_decisions.md` | decisions sound + cited |
| 2 Manual install | `/app-manual-install` | `manual_install.md` | SSH + UI login/smoke test |
| 3 Ansibilize | `/app-ansibilize` | playbook + StackScript | inline review + lint clean |
| 4 Deploy | `/app-deploy` | `e2e_testing.md` | clean fresh deploy + smoke tests |
| 5 Config validation | `/validate-config` | `validation_findings.md` | every directive classified |
| 6 Regression tests *(fork — pick one by app surface)* | `/ui-regression-tests` (web UI) **or** `/backend-regression-tests` (headless) | `ui_testing.md` / `backend_testing.md` + `tests/regression_tests/` suite files | full suite green on a fresh redeploy |
| 7 README + PR | `/app-pr` | app `README.md` (written **last**) | PR review, CI green |
| Docs *(as needed)* | `/app-docs` | public Linode Docs guide (`index.md`) | operator previews + opens the docs PR |

## The handoff file — `.documentation/<app>/STATE.md`

Every skill **reads** this at start and **writes** it at end. It's the connective tissue: where
the pipeline is, which boxes/stackscripts exist, the upstream clone + SHA, and the next step +
checkpoint. (`.documentation/` is a blank mount point committed in `marketplace-claude-skills` and
symlinked into `marketplace-apps`; the per-app working notes inside it are gitignored, never
committed.) The template is bundled at `.claude/skills/backport-start/templates/state.md`.

**Where to review at each STOP.** Every phase writes its artifact into `.documentation/<app>/`
(`STATE.md`, `architecture_decisions.md`, `manual_install.md`, `e2e_testing.md`,
`validation_findings.md`, `ui_testing.md`, `backend_testing.md`, `pr_description.md` — see the table's "Owns artifact"
column). When a
skill stops at its manual-review checkpoint, that directory is where you read its work before
running the next command.

## Core principles (enforced by every skill)

- **Grounding / no hallucination.** Every decision cites a source — a doc URL, a repo `file:line`+SHA,
  or an empirical observation (command + output + box id). Anything ungroundable is flagged as an
  OPEN QUESTION and the skill STOPS. No guessing.
- **Claude never pushes to GitHub.** Pushing (and merging) is always a manual operator step. The
  `/app-deploy` fix loop pauses for the operator to review + push before each fresh redeploy.
- **Claude never runs destructive commands without permission.** `rm -rf` (e.g. cleaning up
  leftover lint artifacts) prompts the operator first.
- **README is written last** (`/app-pr`), after the validated final version is known, and is
  explicitly a manual-review starting point — never blindly trusted.
- **Back up before destructive edits**; remove the backup once the new version is verified.
- **Linode access is via an optional MCP** (see setup below) — its token lives in your user-scope
  config, never in any repo. It's a convenience; you can create the Linodes yourself instead.
- **Reference apps** are curated in [`shared/reference-apps.md`](shared/reference-apps.md), updated
  by PR. The `:start` skills read it and cite the apps' actual files.

## Configure the Linode MCP (optional)

The deploy/manual-install skills *can* drive Linode (create boxes, manage StackScripts) through an
MCP server, so you don't have to switch to Cloud Manager mid-pipeline. It's a **convenience, not a
requirement** — skip it and create the Linodes yourself if you'd rather not grant API access;
everything else in the pipeline still works.

The team uses [`linode-mcp`](https://github.com/josephcardillo-akamai/linode-mcp). To wire it up,
add it to your **user-scope** config (`~/.claude.json`), not the repo, and **name the server
`linode-team`** — the skills reference its tools as `mcp__linode-team__*`, so that exact name is
what makes them resolve (name it anything else and you'd run the MCP tools yourself):

```bash
claude mcp add linode-team --env LINODE_API_TOKEN=<token> -- uv run python server.py
```

Then verify: `list_linodes` via the MCP returns the team account's instances.

**Scope the token tightly.** Prefer a **create-only** credential so the MCP can never delete the
wrong resource. One wrinkle: a legacy Personal Access Token can't be create-only — its Read/Write
setting includes *delete* — but the newer Identity & Access **creator roles** (e.g.
`account_linode_creator`) can. Those roles attach to a *user*, and a token inherits its user's
permissions, so generate the token under a dedicated create-only user. The pipeline never
auto-deletes Linodes, so tearing down a test box is a manual Cloud Manager step regardless.

There is intentionally **no `.mcp.json` in this repo**, so no token is ever in version control.
`.claude/settings.local.json` and `.claude/*.lock` are gitignored for the same reason.
`.reference/` (upstream clones) and the contents of `.documentation/` (per-app working notes — the
directory itself is a committed mount point, symlinked into `marketplace-apps`) are gitignored too.

## Utility skills & commands

- `/validate-config` — Phase 5, the empirical config-directive matrix. Now a skill
  (`.claude/skills/validate-config/`) so both Claude Code and Copilot CLI discover it.
- `/setup-cloud-manager-dev` — sets up a Cloud Manager development environment (separate from the
  app pipeline; useful when the team makes Cloud Manager PRs).
