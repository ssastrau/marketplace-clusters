---
description: Phase 4 — deploy the app from the pushed branch via a real team StackScript, monitor to completion, and run a two-tier diagnose/fix loop (fix-on-VM then mirror-and-push) until a clean fresh deploy. User-invoked only.
disable-model-invocation: true
arguments: [app]
---

# App: Deploy (Phase 4 — Fresh StackScript Deploy + Fix Loop)

Deploy the app from the working branch via a real team StackScript, monitor to completion, and on
failure run a two-tier fix loop until a clean fresh deploy. This proves the playbook works
end-to-end from a clean box, exactly as a marketplace customer would experience it.

Shared by both paths. Reads `STATE.md`; run after `/app-ansibilize`. The live box this produces is
also what `/validate-config` (Phase 5) validates against.

## Usage
```
/app-deploy <app> [--region us-east] [--type g6-standard-2]
```

## Critical rule — Claude never pushes to GitHub
The StackScript clones the **remote** branch, so a fix can only be *deployed* after it's pushed.
Claude applies and commits fixes locally, then **STOPS for the operator to review and push.**
Pushing is always a manual step. Do not `git push`.

## StackScript mechanics
- **Category specifics:** consult `.claude/shared/reference-apps.md` for the app's archetype bucket
  and skim the newest member's StackScript for category-specific needs — e.g. GPU driver / NVIDIA
  setup (bucket 1), multi-service compose port surfaces in UFW (bucket 3), installer-endpoint smoke
  tests (bucket 7). Lightweight cross-check, not a full scaffold.
- The deploy StackScript's `# BEGIN CI-GH` block carries `GH_USER` + `BRANCH`. In the team Cloud
  Manager copy, **set just those two** to the operator's fork + working branch so the box clones
  the right code; everything else is identical to the repo copy.
- **Updating the StackScript:** the `linode-team` MCP now exposes `update_stackscript` (partial
  update — only the fields you pass change, and the StackScript **ID is preserved**, unlike
  delete+recreate). Use it to push a revised script in place and set a `rev_note`.
  (`create_stackscript` / `delete_stackscript` / `list_stackscripts` are still available.)

## Process

### Phase 4a — Create the StackScript + deploy
1. Read `STATE.md` for the app dir, branch, and any prior stackscript id.
2. Confirm the working branch is **pushed** to the operator's fork. If not, STOP and ask the
   operator to push. Create the team StackScript via `mcp__linode-team__create_stackscript` with
   `GH_USER`/`BRANCH` set to that fork+branch (delete+recreate if one already exists). Record the
   stackscript id in `STATE.md`.
3. Build a representative UDF payload (generate secrets, don't hardcode). Deploy a fresh Ubuntu
   24.04 Linode via `mcp__linode-team__create_linode` with that payload, **a generated `root_pass`,
   AND the operator's SSH pubkey**. Record box id/ip in `STATE.md`.
   - **Keep the work dir on failure (enables the 4c inner loop):** the StackScript's EXIT trap
     `rm -rf`s `/tmp/marketplace-apps` on any failure **unless `DEBUG` is set to a non-`NO` value**.
     Before deploying an iteration box you intend to fix on-VM, set `DEBUG="yes"` at the top of the
     deploy StackScript (uncomment the `#DEBUG="NO"` line, set it to `yes`) so a failed playbook
     leaves the work dir intact to edit + re-run. Reset it (remove `DEBUG` / set back to `NO`) for the
     **final** clean-deploy verification — that pass must run in normal production mode.

### Phase 4b — Monitor
4. Poll: `get_linode` until `running`, then SSH and tail `/var/log/stackscript.log` to completion.
   Watch for the Ansible play recap and the final credential output.

### Phase 4c — Two-tier fix loop
**On failure, work the inner loop on the VM first (no GitHub), then mirror + push.**

**Inner loop — on the VM, no GitHub round-trips** (requires the work dir to have survived the
failure — see the `DEBUG` note in 4a; without it the EXIT trap already wiped `/tmp/marketplace-apps`
and you must skip straight to mirror+push+redeploy)**:**
   a. SSH into the box, read `/var/log/stackscript.log` + relevant service logs, **diagnose the
      root cause and cite the actual log line.**
   b. Apply the fix directly to the task file under
      `/tmp/marketplace-apps/apps/linode-marketplace-<app>` on the box.
   c. Re-run the playbook from there with the venv active:
      ```bash
      cd /tmp/marketplace-apps/apps/linode-marketplace-<app>
      source env/bin/activate
      ansible-playbook -v site.yml      # (and provision.yml first if the failure was in provision)
      ```
      Tasks are idempotent and this repo uses **no tags**, so already-completed tasks re-run as
      `ok`/`skipped` and the play effectively **resumes at the failure** — no need to rebuild the
      box. (`--start-at-task "<name>"` exists but is unreliable across this repo's `include_role`
      loops and skips handlers — don't rely on it.)
   d. Repeat (a)–(c) until the playbook completes clean **on the VM**.

**Then — mirror, push, redeploy:**
   e. Mirror every VM-side fix into the **local repo**. Back up a file before a risky edit; remove
      the backup once verified. Commit locally with a clear message.
   f. **STOP — operator review + push.** Show the diff. The operator reviews and `git push`es.
      Claude does not push.
   g. After the push, create a **fresh** box from the updated branch (Phase 4a) and re-monitor.
      A fresh deploy must succeed with **no** VM-side edits — that's the real pass condition.
   h. Loop e–g until a clean fresh deploy.

### Phase 4d — Smoke test + hand off
5. On a clean fresh deploy, run the smoke-test suite (mirror the checks from `manual_install.md`):
   HTTPS front page 200, HTTP→HTTPS 301, installer endpoint 4xx, admin login, DB port not public,
   services `active`, credentials present. Record pass/fail + evidence in
   `.documentation/<app>/e2e_testing.md`.
6. Leave the box **up** (target for `/validate-config`). Update `STATE.md`: mark `deploy`
   done, record stackscript id + box id/ip, set `next_step: /validate-config`.

## Output
- `.documentation/<app>/e2e_testing.md` — fresh-deploy smoke results (this command owns it).
- A working team StackScript + a live clean deploy box.
- `STATE.md` updated.

## STOP — manual review (checkpoint)
- [ ] Operator reviewed and pushed **each** fix (Claude never pushed).
- [ ] Final fresh deploy completed clean from the branch with **no** VM-side edits.
- [ ] All smoke tests pass; `e2e_testing.md` records the evidence.
- [ ] The deploy box is left up for config validation.

**Next:** `/validate-config <app> --instance <deploy-box-ip>`
