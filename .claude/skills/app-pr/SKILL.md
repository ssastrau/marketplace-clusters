---
description: Phase 7 (last) — write the app README from the validated final version and DRAFT the PR in the repo's .github/pull_request_template.md format for operator review. Does NOT create the PR. Claude never pushes, merges, or opens the PR. User-invoked only.
disable-model-invocation: true
arguments: [app]
---

# App: PR (Phase 7 — README + PR draft)

Runs **last**, only after `/app-deploy` and `/validate-config` have confirmed the final
version. This is the **only** command that writes `apps/linode-marketplace-<app>/README.md`. It also
**drafts** the pull-request description in the repo's template format — for the operator to review
and submit. It does **not** open the PR.

Shared by both paths. Reads `STATE.md` + all four `.documentation/<app>/*.md` artifacts.

## Usage
```
/app-pr <app>
```

## Critical rules
- **Claude never pushes, merges, or creates the PR.** This skill *drafts* the README and the PR body
  for the operator to review and submit themselves. Do **not** run `gh pr create`.
- **The generated README + PR draft are starting points, not authoritative.** Like everything in this
  pipeline they **must be manually reviewed** by the operator before submission. Flag uncertain spots
  with inline `<!-- REVIEW: ... -->` notes rather than guessing.

## Process

### Phase 7a — Write the README
1. Pick the matching bundled template and fill it from the validated artifacts (cite nothing from
   memory — pull names/ports/versions from `architecture_decisions.md`, `manual_install.md`, the
   playbook, and `e2e_testing.md`):
   - **Standard app** → `${CLAUDE_SKILL_DIR}/templates/README-standard.md` (service / CMS / HashiCorp-style).
   - **Model-serving / AI app** → `${CLAUDE_SKILL_DIR}/templates/README-model.md` (GPU inference / vector DB).
   Use the team branding (motd/README say **Akamai Cloud Compute**, app type **Quick Deploy App**).
2. Write it to `apps/linode-marketplace-<app>/README.md`, with `<!-- REVIEW: ... -->` on anything a
   human must confirm (sample workload, scaling, screenshots).

### Phase 7b — Draft the PR body (repo template format)
3. **Read the repo PR template** `.github/pull_request_template.md` and fill **every** section from
   the artifacts (don't invent — leave a `<!-- REVIEW -->` placeholder where the operator must decide):
   - **Description** — what the app is + what this PR adds (from `architecture_decisions.md`).
   - **Type of Change** — tick the box: `New App` for `/newapp-start` apps; `Bug Fix` / `Update / Refactor`
     for backports — match `STATE.md` `type`.
   - **Linked Issues** — leave a placeholder for the operator (any tracking ticket).
   - **Changes** — list the affected paths (`apps/linode-marketplace-<app>`,
     `deployment_scripts/linode-marketplace-<app>`) and what each contains (roles, StackScript, etc.).
   - **How to Test** — keep it **light and hands-on**, not exhaustive:
     - Deploy config: UDFs (sudo user, disable_root, domain/subdomain/SOA email), plan/region/image,
       and that credentials land in `/home/<user>/.credentials`.
     - A short *user-level* exercise of the app's primary function — what a real user would do once
       it's up. Tailor to the app: an **agent/flow builder** → log in, drag a few nodes onto the
       canvas, connect them, run a small flow (e.g. document ingestion → text split → embedding); a
       **CMS** → log in + create a sample post; a **database** → connect + run a query; an **API/LLM
       server** → an authenticated sample request. One representative path is enough.
     - Expected outcome + a pointer to the `e2e_testing.md` smoke results.
   - **Checklist** — tick what the pipeline already satisfied (ansible-lint passes, deployed + tested
     e2e on Akamai Compute, app reachable/functional, no hardcoded secrets, docs updated); leave
     "Relevant reviewers assigned" for the operator.
   - **Additional Notes** — the `validation_findings.md` summary (LOAD-BEARING / DEFENSIVE / any
     DEAD-CODE removed), known limitations (e.g. a floating `:latest` image tag), follow-ups, and an
     explicit note that the README + this PR body are first drafts pending the operator's review.
4. Write the filled PR body to `.documentation/<app>/pr_description.md`.

### Phase 7c — STOP (operator reviews + submits)
5. Present the README + the drafted `pr_description.md`. The operator reviews/edits both, confirms the
   branch is pushed, and **creates the PR themselves** (and assigns reviewers). Claude does not open it.
6. Update `STATE.md`: mark `pr` drafted; record the `pr_description.md` path (and the PR URL later,
   once the operator submits).

## Output
- `apps/linode-marketplace-<app>/README.md` — user-facing doc (review required).
- `.documentation/<app>/pr_description.md` — the drafted PR body in the repo template format.
- `STATE.md` updated.

## STOP — manual review (checkpoint)
- [ ] Operator has read the README and confirms it's accurate (not blindly trusted).
- [ ] PR draft follows `.github/pull_request_template.md`, every section filled or `<!-- REVIEW -->`-flagged.
- [ ] How-to-Test is a light, real user-level exercise of the app + the deploy config.
- [ ] Operator submits the PR (Claude did not open it); reviewers assigned; CI green.
