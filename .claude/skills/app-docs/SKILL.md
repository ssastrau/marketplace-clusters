---
description: Write the public Linode Marketplace ("Quick Deploy Apps") guide for an app and place it in the docs repo (linode/docs). Reads the app's code + .documentation/<app> design notes for ground truth, fills the marketplace-guide template, and DRAFTS index.md for operator review. Does NOT commit, push, or open a docs PR. User-invoked only.
disable-model-invocation: true
arguments: [app, docs_repo]
---

# App: Docs (public marketplace-docs guide)

Writes the customer-facing **Linode Marketplace guide** (`index.md`) for an app into the
**docs** repo (`github.com/linode/docs`). This is the public guide that ships at
`linode.com/docs/marketplace-docs/guides/<app>/` — distinct from the in-repo `README.md` that
`/app-pr` writes. **Standalone:** it reads the app source and the `.documentation/<app>/` design
notes for ground truth, but does **not** read or write `STATE.md` and does not assume the
`/app-vet → … → /app-pr` pipeline ran.

## Usage
```
/app-docs <app> [docs-repo-path]
```
Parse arguments from `$ARGUMENTS`:
- `$app` — the app slug, e.g. `langflow` (the repo folder is `apps/linode-marketplace-<app>`). Accept
  either `langflow` or `linode-marketplace-langflow` and normalize to the bare slug.
- `$docs_repo` *(optional)* — absolute path to the local `linode/docs` checkout.

## Critical rules
- **Claude never commits, pushes, or opens the docs PR.** This skill *drafts* `index.md` only. The
  operator previews it (`hugo server`), proofreads, commits, and opens the PR themselves.
- **Ground every fact — cite nothing from memory.** Ports, services, software versions, default
  usernames, the credentials path, config fields, and sizing all come from the app's code, the
  deploy script, and the `.documentation/<app>/` artifacts. If a value can't be grounded (e.g.
  `marketplace_app_id`, which Akamai assigns at publish time), insert a `<!-- REVIEW: ... -->`
  placeholder and continue — **do not guess**.
- **Screenshots can't be auto-captured.** Emit the image markdown + a `<!-- REVIEW: capture + add
  screenshot -->` note; the operator adds the PNG.
- **The draft is a starting point, not authoritative.** Like everything else in this team's flow it
  must be manually reviewed before the docs PR is opened.

## Resolve paths (do this first)
- **App source:** `apps/linode-marketplace-<app>/` — `README.md`, `site.yml`,
  `roles/<app>/{defaults/main.yml,tasks/*,templates/*}`, `group_vars/linode/vars`.
- **Deploy script:** `deployment_scripts/linode-marketplace-<app>/<app>-deploy.sh` — the `#<UDF …>`
  declarations are the **Marketplace configuration options** the user sees in Cloud Manager.
- **Design notes:** `.documentation/<app>/` — `architecture_decisions.md`, `manual_install.md`,
  `e2e_testing.md`, `validation_findings.md` (any subset that exists).
- **Docs repo:** `$docs_repo` if given → else a sibling `../docs` of this repo → else **STOP and ask
  the operator** for the path. Do not invent one.
- **Output target:** `<docs-repo>/docs/marketplace-docs/guides/<app>/index.md`. Create the
  `guides/<app>/` folder if it doesn't exist. **Before writing, scan two or three existing sibling
  guides** in `<docs-repo>/docs/marketplace-docs/guides/` (e.g. `chroma`, `arangodb`, plus the closest
  app type) to match the current house conventions — they evolve.
- **Canonical scaffold:** the docs repo ships an official archetype at
  `<docs-repo>/archetypes/marketplace.md` (used by `hugo new marketplace-docs/guides/<app>/index.md
  --kind marketplace`). The bundled `templates/marketplace-guide.md` is that archetype **extended**
  with the fields and shortcodes every recent guide now includes (`aliases`, `marketplace_app_id`,
  `marketplace_app_name`, and the limited-user / custom-domain / special-char shortguides). If the
  archetype has drifted from the sibling guides, trust the **sibling guides**.

## Grounding contract
Every concrete claim in the guide maps to a source:

| Guide element | Grounded from |
|:---|:---|
| Intro / what the app is | upstream docs link + `README.md` + `architecture_decisions.md` |
| Supported distributions | deploy script / `architecture_decisions.md` (e.g. Ubuntu 24.04 LTS) |
| Recommended plan / sizing | upstream docs (cite) or `architecture_decisions.md`; the deploy `linode-config.sh` `LINODE_TYPE` is the tested plan |
| `<App> Options` (config fields) | the `#<UDF …>` label lines in the deploy script |
| Ports / exposed surface | `roles/<app>/templates/*compose*.j2`, `nginx.conf.j2`, `ufw_rules.yml`, architecture D2 |
| Default username / auth model | compose env (`*_SUPERUSER`, etc.), architecture D3/D4 |
| Credentials retrieval | `roles/post` / `provision.yml` → `/home/<user>/.credentials` |
| Software Included | `README.md` "Software Included" + the compose images + `defaults/main.yml` versions |
| How it's accessed/verified | `e2e_testing.md` smoke tests (the real URLs/endpoints that returned 200) |

If two sources disagree (e.g. `README.md` says one version but an older `e2e_testing.md` run shows
another), prefer the **currently-shipped code** (`defaults/main.yml`, the compose template) and note
the discrepancy with a `<!-- REVIEW -->` if unsure.

## Process

1. **Read the sources** listed under *Resolve paths* — the app `README.md`, the deploy-script UDF
   lines, the compose/nginx templates and `defaults/main.yml` (versions, ports), and the
   `.documentation/<app>/*` notes (install method, auth model, credentials, smoke-tested access path).
2. **Pick the access pattern** the guide's "Getting Started" section should use, from how the app is
   actually reached (per `e2e_testing.md`):
   - **Web UI with native login** → "Accessing the `<App>` Web Interface" (browse to the URL, log in
     with the generated superuser; password from the credentials file).
   - **API-/client-only (no UI)** → "Obtain Your Credentials" / "Connect Your Application" (retrieve
     API keys, point a client at the server). See `chroma` / `weaviate` for this shape.
3. **Fill the template** `${CLAUDE_SKILL_DIR}/templates/marketplace-guide.md` from the grounded
   facts. Keep the section order and shortcode includes exactly as in the template.
4. **Write** `index.md` to the output target. Flag every screenshot and any ungrounded metadata with
   `<!-- REVIEW: ... -->`.

## Docs-repo CONTRIBUTING.md compliance
The docs repo runs three CI gates on every PR (per its `CONTRIBUTING.md`). Pre-empt all three:
- **Blueberry** (frontmatter validator) — emit **every** frontmatter field the sibling guides use,
  correctly quoted. Don't omit a field to dodge the gate; flag an unknown value with `<!-- REVIEW -->`.
- **Vale** (spell-check) — US spelling; wrap product/proper nouns and code identifiers in backticks
  or code fences so they aren't flagged; keep prose in the house voice (see below).
- **Docs404** (internal-link scan) — internal links use relative `/docs/...` paths that resolve;
  `aliases` follow the `/products/tools/marketplace/guides/<slug>/` +
  `/guides/<slug>-marketplace-app/` shape; no broken anchors (anchors must match generated heading IDs).
- **Images** — co-located in the `guides/<app>/` folder, linked by **bare filename**
  (`![Title](app-login.png)`), per the writer's formatting guide.

## House style (match the existing guides)
- Second-person, imperative, present tense ("Open your web browser and navigate to…").
- Code/commands in ` ```command ` fences; placeholders as `{{< placeholder "DOMAIN" >}}`.
- Callouts via `{{< note >}}` / `{{< note type="warning" >}}`.
- Required config fields marked `*(required)*`; `## Software Included` as a two-column table.
- Reuse the standard shortcodes via `{{% content "…-shortguide" %}}` rather than re-writing boilerplate
  (deploy steps, verify, limited-user fields, custom-domain fields, special-char limits, update note).
- Style authority: the [Linode Writer's Formatting guide](https://www.linode.com/docs/linode-writers-formatting-guide/).

## Output
- `<docs-repo>/docs/marketplace-docs/guides/<app>/index.md` — the drafted public guide (review required).

## STOP — manual review (checkpoint)
- [ ] Frontmatter is complete and quoted (Blueberry-clean); `marketplace_app_id` filled or `<!-- REVIEW -->`.
- [ ] Every concrete claim (ports, default user, credentials path, versions, options) traces to a source; gaps are `<!-- REVIEW -->`-flagged, not guessed.
- [ ] Section order + shortcode includes match current sibling guides; prose is in the house voice (Vale-clean).
- [ ] Internal `/docs/...` links and `aliases` resolve (Docs404); screenshots flagged for capture.
- [ ] Operator previews with `hugo server`, proofreads, then branches from `develop`, commits only `docs/marketplace-docs/guides/<app>/`, and opens the docs PR themselves (Claude did not).
