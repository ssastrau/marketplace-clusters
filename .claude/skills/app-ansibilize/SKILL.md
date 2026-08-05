---
description: Phase 3 — convert manual_install.md into a marketplace Ansible playbook + StackScript following this repo's structure, reusing helper roles, then lint clean. User-invoked only.
disable-model-invocation: true
arguments: [app]
---

# App: Ansibilize (Phase 3 — Convert the Manual Install to a Playbook)

Convert `manual_install.md` into a proper marketplace Ansible playbook + StackScript, using the
live manual-install box as the reference for what "correct" looks like. Ends with a clean local
lint.

Shared by both paths. Reads `STATE.md`; run after `/app-manual-install`.

## Usage
```
/app-ansibilize <app>
```
Reads `.documentation/<app>/{STATE.md,manual_install.md,architecture_decisions.md}`.

## Grounding contract
Every task in the playbook must trace to a real step in `manual_install.md` or a directive in
`architecture_decisions.md`. Don't invent tasks. When unsure whether a manual step is
load-bearing, mark it for `/validate-config` rather than dropping or cargo-culting it.

## Pick the reference app to scaffold from
Use `.claude/shared/reference-apps.md`: classify this app's archetype (from
`architecture_decisions.md` + `manual_install.md`) → match one bucket → rank that bucket's members
by date-added (`git log --diff-filter=A --format=%cs -- apps/linode-marketplace-<m> | tail -1`,
newest first) → scaffold from the **newest 1–2 members**, reading their `site.yml`, `provision.yml`,
`roles/<app>/`, and StackScript. Newer apps track current conventions; cite `file:line` for patterns
you copy.

## What's boilerplate vs. written-fresh (empirical — verified across openbao, memgraph, redis, wordpress, hashicorp-nomad)
Apply this rule to whichever reference app you scaffolded from above.
Source of truth: `CLAUDE.md` §"Standard App Structure".

| File | Treatment |
|---|---|
| `ansible.cfg` | **Copy verbatim** (byte-identical across apps; only `roles_path` matters and it's standard) |
| `.yamllint` | **Copy verbatim** |
| `.ansible-lint` | **Copy verbatim** |
| `collections.yml` | Copy the collection LIST from the reference app, then **re-pin every entry to the latest published Galaxy version** (see "Latest-pins rule" below) — never inherit the reference app's pins |
| `requirements.txt` | Copy the package list, add app-specific deps (e.g. `PyMySQL`), then **re-pin every entry to the latest published PyPI version** (see "Latest-pins rule" below) — never inherit the reference app's pins |
| `site.yml` | Same pattern; **edit only the role loop list** (`common` → `<app>` → `post`) |
| `provision.yml` | Same pattern; **edit the generated cred var names** for this app |
| `group_vars/linode/vars` | Create as a **blank (0-byte) file** — populated at deploy time by the StackScript `udf()` + `provision.yml`. No comment. |
| `roles/common/` | ~95% identical; copy and review (hostname, DNS, sshkey, securessh, update_pkgs, ufw, fail2ban) |
| `roles/post/` | Same pattern; **edit the credentials block** for this app's secrets |
| `roles/<app>/` | **Write fresh** — this is where the real per-app work lives |

**Latest-pins rule (operator mandate, 2026-07-07):** the pins a reference app carries are a
snapshot of when *that* app shipped — copying them scaffolds stale versions (langfuse initially
inherited chroma's ansible 13.5.0 / linode.cloud 0.41.1 when 14.1.0 / 0.47.0 were current).
At authoring time, check every pin and set it to the latest published version:

```bash
# PyPI (each package in requirements.txt):
curl -s https://pypi.org/pypi/<pkg>/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"
# Galaxy (each collection in collections.yml):
curl -s "https://galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections/index/<ns>/<name>/" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['highest_version']['version'])"
```

Then Phase 3c's lint venv doubles as the compatibility check — it installs exactly these pins.
(zsh footgun: don't name a loop variable `path` — it aliases `PATH` and breaks every subsequent
command in the loop.)

**Branding (fix it when adapting a reference app — older apps carry stale wording):**
- motd (`roles/post/templates/motd.j2`): `Akamai Connected Cloud <App> Quick Deploy App` — **not**
  "Marketplace App".
- Platform name everywhere (motd, README): **Akamai Cloud Compute** — **not** "Linode" or
  "Akamai Cloud (Linode)".

## Process

### Phase 3a — Scaffold the structure
1. Create the role tree under `apps/linode-marketplace-<app>/` per the table above
   (`ansible.cfg`, `collections.yml`, `requirements.txt`, `provision.yml`, `site.yml`,
   `group_vars/linode/vars`, `roles/common` → `roles/<app>` → `roles/post`, `.ansible-lint`,
   `.yamllint`, `README.md` stub). Copy verbatim / version-pin / write-fresh as the table dictates.
2. Create the StackScript set under `deployment_scripts/linode-marketplace-<app>/`:
   - `<app>-deploy.sh` — from `${CLAUDE_SKILL_DIR}/templates/stackscript.sh`: CI-MODE block,
     `#<UDF ...>` declarations, the `GH_USER`/`BRANCH` CI-GH fork-override block, `WORK_DIR`
     (`/tmp/marketplace-apps`) + `MARKETPLACE_APP`, the `udf()` function with **string→boolean UDF
     conversion** (`Yes`→`true`), venv + `pip install -r requirements.txt` +
     `ansible-galaxy install -r collections.yml`, the
     `ansible-playbook -v provision.yml && ansible-playbook -v site.yml` invocation, and final
     credential output.
   - `linode-config.sh` — from `${CLAUDE_SKILL_DIR}/templates/linode-config.sh`: region / type /
     image, exported to `$GITHUB_ENV` for CI.
   - `test-vars.sh` — from `${CLAUDE_SKILL_DIR}/templates/test-vars.sh`: UDF defaults for CI
     testing (sourced before the deploy script runs).

### Phase 3b — Ansibilize the steps (modules over shell)
3. Translate each command from `manual_install.md` into declarative Ansible tasks per `CLAUDE.md`.
   Where a command came from an upstream install script (noted in `manual_install.md` as
   `install.sh:NN @ <sha>`), convert **that underlying command**, never a call to the script:
   - `get_url` over curl/wget; `community.docker.*` for Docker; `systemd_service` for services;
     `debconf` for package config; `template`/`copy`/`lineinfile`/`blockinfile` for files.
   - `wait_for` / container-readiness polling instead of `pause`/sleep.
   - Booleans `true`/`false`, never `"yes"`/`"no"`. Defaults on every var for CI.
4. Move all secrets to `provision.yml` (generated via `set_fact` + `lookup('password', ...)`),
   surfaced through `group_vars` and written to `/home/<user>/.credentials` by `roles/post`.
   - **Cross-role variables (`include_role` scoping):** any var referenced in **more than one role**
     — an app's superuser name, DB name, DB user, etc. used by both `roles/<app>` and `roles/post` —
     must be written to `group_vars/linode/vars` by the StackScript `udf()` (play-wide), **not** put
     in one role's `defaults/main.yml`. `include_role` scopes a role's `defaults/` to that role only,
     so a value defined in `roles/<app>/defaults` is **undefined** when `roles/post` runs and the play
     fails at deploy time (langflow hit exactly this: `'langflow_superuser' is undefined` in the post
     creds task). Role `defaults/` are fine only for vars used **within that single role**. Generated
     secrets follow the same play-wide path but originate in `provision.yml` instead of the `udf()`.
5. Reuse helper roles from `apps/linode_helpers/roles/` wherever possible — `certbot_ssl`, `ufw`,
   `securessh`, `fail2ban`, `hostname`, `update_pkgs`, `data_exporter`, `docker`, `database`.
   - **nginx reverse proxy (apps on a non-standard port):** ship the vhost as
     `roles/<app>/templates/nginx.conf.j2` and select the certbot flow by passing `webserver_stack`
     as a `vars:` on the `certbot_ssl` import (`vars: { webserver_stack: lemp }`) — like
     chroma/deepseek — **not** through the StackScript `udf()`. Add a canonical-host redirect at the
     **top** of `nginx.conf.j2` so the bare IP / any non-FQDN Host 301s to the canonical hostname
     instead of certbot's default 404:
     ```nginx
     # raw IP / any non-FQDN Host -> canonical https://FQDN
     server {
         listen 80 default_server;
         server_name _;
         return 301 https://{{ _domain }}$request_uri;
     }
     server {
         listen 80;
         server_name {{ _domain }};
         location / { proxy_pass http://127.0.0.1:{{ app_port }}; ... }
     }
     ```
     `certbot --nginx` then attaches `listen 443 ssl` to the FQDN block and moves its port-80
     handling into its own managed block; the `default_server` block is left intact to catch every
     other Host, and renewal stays safe (verified `certbot renew --dry-run` with the `default_server`
     present). Validated on langflow 2026-06-10.
6. **SSH hardening placement:** `securessh` in `roles/common` right after `sshkey`, gated on
   `disable_root` — matching current practice. There is **no** "harden last" requirement in the
   playbook (that was only a manual-session precaution).

### Phase 3c — Local lint (clean before review)
7. Lint via the **committed wrapper scripts** (canonical per `AGENTS.md` — they apply the repo's
   custom configs), in a recent-Python venv (the macOS default 3.10 is too old; use 3.12+):
   ```bash
   cd apps/linode-marketplace-<app>
   python3 -m venv env && source env/bin/activate
   pip install -r requirements.txt && ansible-galaxy install -r collections.yml
   # from repo root:
   tests/static_code_analysis/yaml_configs/check_yaml_configs.sh apps/linode-marketplace-<app>
   tests/static_code_analysis/ansible_playbooks/check_ansible_playbooks.sh apps/linode-marketplace-<app>
   tests/static_code_analysis/shell_scripts/check_shell_scripts.sh deployment_scripts/linode-marketplace-<app>
   ansible-playbook -i localhost, -c local --syntax-check site.yml
   ```
8. **Clean the lint artifacts before any `git add`:** `env` and `.ansible` are intentionally NOT
   gitignored — remove them by hand. **This is a destructive command: ask the operator for
   explicit permission before running `rm -rf env .ansible`** (never run `rm -rf` unprompted). Back
   up any file before a risky edit; remove the backup once the new version is verified.

### Phase 3d — Hand off
9. Update `STATE.md`: mark `ansibilize` done, record the app dir + stackscript path, set
   `next_step: /app-deploy`.

## Output
- `apps/linode-marketplace-<app>/` — the playbook (this command owns it).
- `deployment_scripts/linode-marketplace-<app>/` — `<app>-deploy.sh` + `linode-config.sh` + `test-vars.sh`.
- Clean lint (`check_yaml_configs.sh`, `check_ansible_playbooks.sh`, `check_shell_scripts.sh`, `--syntax-check`).
- `STATE.md` updated.

## STOP — manual review (checkpoint)
Run an inline, `CLAUDE.md`-grounded review (the §"Code Review Checklist" + §"Marketplace App
Deployment Standards" — there is no separate review agent), then have the operator confirm:
- [ ] Every task traces to `manual_install.md`; no cargo-culted directives.
- [ ] Modules used over shell; booleans `true`/`false`; vars have CI defaults.
- [ ] Secrets generated in `provision.yml`, nothing hardcoded; `roles/post` writes `.credentials`.
- [ ] Helper roles reused; `securessh` after `sshkey` gated on `disable_root`.
- [ ] Local lint clean and the lint artifact dirs (`env`, `.ansible`) are removed (with permission).

**Next:** `/app-deploy`
