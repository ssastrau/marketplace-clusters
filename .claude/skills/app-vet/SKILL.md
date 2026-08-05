---
description: Phase 0 (triage) — vet a candidate piece of software against what already exists in the marketplace and render a grounded verdict — new app, addon, already-exists, not-deployable-as-named, or not-suitable — before any research spend. User-invoked only.
disable-model-invocation: true
arguments: [app, --repo, --docs]
---

# App Vet (Phase 0 — Triage Before the Pipeline)

Optional front-end to the whole pipeline. Before `/backport-start` or `/newapp-start` spends a
research phase (and a live box) on a candidate, this skill answers the prior question: **should
this be a marketplace app at all?** It renders one of five verdicts, each grounded in what
actually exists in this repo today, and routes to the right next command.

Why this phase exists: candidates fail in ways the `:start` skills assume away — the software is
a *library* whose deployable form is a different product (LangGraph vs. langgraph-cli/Platform);
it's already covered by an existing app; or it's really an **add-on** (a lightweight agent that
enhances other deployments) and belongs in `apps/linode_helpers/roles/addons/`, not as a 96th
app directory.

## Usage
```
/app-vet <app> [--repo <git-url>] [--docs <url>]
```
Parse `--repo` and `--docs` from `$ARGUMENTS`; `$app` is the first positional.

## Arguments
- `<app>`: short candidate name, lowercase (e.g. `langgraph`, `fluent-bit`). Used for
  `.documentation/<app>/`.
- `--repo <git-url>`: optional upstream source repository. Strongly recommended — without it the
  deployability check leans entirely on docs found via search.
- `--docs <url>`: optional pointer to the official documentation root (otherwise discovered via
  `WebSearch`).

## Verdict space

| Verdict | Meaning | Next |
|---|---|---|
| `new-app` | Deployable single-node server, novel to the marketplace | `/newapp-start` — or `/backport-start` if a legacy StackScript exists |
| `addon` | Optional agent that enhances *other* deployed apps | `/addon-build` |
| `already-exists` | Covered by an existing `apps/linode-marketplace-<x>` (name it) | STOP — or scope a *change* to that app instead |
| `not-deployable-as-named` | Library / SDK / SaaS-only / desktop app — no self-hostable single-node server under this name | STOP — name the deployable sibling product if one exists, and search for an OSS equivalent (0b step 8); re-vet whichever fits |
| `not-suitable` | Deployable, but structurally fails marketplace standards (e.g. unauthenticatable open data ingestion, prohibitive license) | STOP — record which `CLAUDE.md` mandate it cannot meet, and search for an OSS equivalent (0b step 8) to redirect to |

Exactly one verdict. If the evidence genuinely supports two (e.g. ships both an agent and a
server console), record the split as an OPEN QUESTION with the evidence for each and STOP for
the operator.

## Grounding contract (non-negotiable)
Every claim in the verdict must cite a source — a **doc URL**, a **repo `file:line` + commit
SHA**, or a **command + its output** (e.g. the `ls apps/` listing that proves novelty). Pull
sources in explicitly; never reason from memory:
- What exists in the marketplace → `ls apps/` and `ls apps/linode_helpers/roles/addons/tasks/`
  **at runtime**. Never trust a remembered inventory — including the bucket lists in
  `.claude/shared/reference-apps.md`, which are diffed against `ls apps/`, not substituted for it.
- Upstream reality → shallow-clone `--repo` into `.reference/<repo>` (gitignored), record the
  commit SHA, and read the *actual* README, Dockerfiles/compose files, and install docs.
- Official docs → `WebFetch` / `WebSearch`, capture the exact URL.

**If a fact cannot be grounded, record it as an OPEN QUESTION and STOP for the operator. Do not guess.**

## Process

### Phase 0a — Existence / duplicate check
1. `ls apps/` (ground truth) and scan `.claude/shared/reference-apps.md` for the candidate by
   name *and* by function (e.g. a candidate metrics store vs. bucket 11's existing members).
   Always diff the taxonomy against the live `ls apps/` — the taxonomy is curated and can lag.
2. Check for a legacy StackScript: `grep -ril '<app>' deployment_scripts/` plus
   `mcp__linode-team__list_stackscripts` if the operator suspects one exists outside the repo.
   A hit routes an eventual `new-app` verdict to `/backport-start` instead of `/newapp-start`.
3. Near-duplicate test: if an existing app covers the same job (e.g. a second S3-compatible
   store, a second password manager), the verdict is `already-exists` unless the operator has
   already stated the marketplace wants both. Name the overlapping app and cite its
   `apps/linode-marketplace-<x>/README.md`.

### Phase 0b — Deployability check
4. Shallow-clone `--repo` into `.reference/<repo>`; record `git -C .reference/<repo> rev-parse HEAD`.
   Read the README, any `docker-compose.yml`/`Dockerfile`, release artifacts, and the install
   section of the official docs.
5. Decide: is there a **self-hostable, single-node server** with an upstream-blessed install
   path (Docker/Compose → official package repo → source → binary, per `CLAUDE.md`'s priority
   order)? Specifically rule out:
   - **Library / SDK / framework** — imported into someone else's code, nothing to run
     (the LangGraph case: the repo is a Python library; the deployable sibling is
     langgraph-cli / LangGraph Platform). Verdict `not-deployable-as-named`; name and cite the
     sibling so the operator can re-vet it.
   - **SaaS-only** — docs describe a hosted control plane with no self-host server release.
   - **Desktop / client app** — runs on the end user's machine, not a Linode.
   - **Ecosystem disambiguation:** when the candidate is one of a family of similarly-named
     products (e.g. LangChain / LangGraph / LangFlow / LangSmith), map the siblings and confirm
     *which* is the deployable product before vetting — a deployable-sounding name can be a library
     while a sibling is the actual app (and vice-versa). Vet the thing that runs, not the brand.
6. **Deployable ≠ wrappable (the IDE-shell trap).** A tool you *can* install on a box isn't a
   marketplace app unless the running box itself delivers the value. **Trace how the tool is
   actually used:** if its real-world use is *embedded in the user's own code / app / runtime
   elsewhere* (a library, an SDK, a locally-run CLI), a dedicated VM — even dressed up with an IDE
   or "dev-environment" shell — has no standalone purpose. The shell is the seductive part: it
   *looks* like `new-app` (it has nginx, certbot, a web UI), but the actual value proposition is
   still just "a library is pre-installed," which the developer can do themselves in their own
   environment. Test: **"If I deployed this box, what does it DO on its own? If the honest answer is
   'it has X installed, ready for me to build something else with,' it's an ingredient, not a
   product."** Ingredients are `not-deployable-as-named` (this is what sank the "LangChain SDK
   dev-environment" idea — same verdict as the langgraph library it wrapped).
7. If deployable, also sanity-check it against the structural `CLAUDE.md` mandates that no
   amount of playbook work can fix (e.g. a data-ingestion service whose protocol cannot carry
   authentication — §6 zero-tolerance). A hard structural conflict → `not-suitable`, citing the
   exact mandate.
8. **OSS-equivalent redirect (don't dead-end a blocked candidate).** Whenever a candidate is
   blocked — library, SaaS-only, license-gated, or structurally `not-suitable` — before you STOP,
   `WebSearch` for an **open-source, self-hostable equivalent** that fills the same user need, and
   name it as a fresh candidate in `vetting.md`. A dead end for one name is often a redirect to
   another (LangSmith → **Langfuse**; the closed/commercial product points at the OSS app that
   actually fits). Record the alternative with its repo/docs URL so the operator can re-vet it.

### Phase 0c — Provider landscape (how other clouds offer it)
9. `WebSearch` how other cloud providers offer the candidate — check at least AWS / Azure / GCP
   marketplaces and the DigitalOcean/Vultr one-click catalogs, plus the vendor's own "deploy"
   page. For each hit, record the **shape** of the offering, because the shape is the signal:
   - **One-click single-VM image on other IaaS marketplaces** → strong positive: there's
     precedent and a reference implementation for a Linode one-click; note what stack/auth they
     ship.
   - **Vendor SaaS / private-offer listing only** (the product is bought *through* a cloud
     marketplace but runs as the vendor's platform) → negative signal: the vendor's deployment
     story funnels to their commercial product, and a community single-node offering has no
     precedent to follow.
   - **Managed service by the cloud itself** (e.g. a hosted flavor of the engine) → neutral:
     validates demand, but check whether the self-host server is feature-complete vs. the
     managed one.
   - **Tutorials / blog posts only** → weak signal either way; not an offering.
10. Fold the landscape into the verdict: a candidate whose only marketplace presence anywhere is
   the vendor selling its own licensed platform leans `not-deployable-as-named` or
   `not-suitable` (record which license/key a self-host deploy would require — a deploy that
   yields a dead box without a customer-supplied paid key needs an explicit operator decision;
   vendor-licensed precedent exists in `apps/linode-marketplace-plesk` /
   `linode-marketplace-cpanel-*`, so it's a judgment call, not an auto-fail). A candidate that
   several other IaaS providers ship as one-click VM images leans `new-app`. Cite every claim
   (listing URL / docs URL); absence of an offering is recorded as "none found" with the search
   performed, not asserted from memory.

### Phase 0d — App vs. addon rubric
11. Inventory the existing add-ons **live**: `ls apps/linode_helpers/roles/addons/tasks/` and read
   `apps/linode_helpers/roles/addons/tasks/main.yml` (the `{ name, file }` include loop) plus the
   "Add-ons: Usage and Extending" section of `apps/linode_helpers/README.md`. As of this
   writing all members are headless observability agents (node_exporter, mysqld_exporter,
   newrelic, alloy, opentelemetry_collector) — but verify, don't assume.
12. Score the candidate. **`addon`** requires ALL of:
   - It **enhances other deployed apps** (agent / exporter / collector / forwarder shape) and
     has **no standalone value on an empty box** — nobody deploys a Linode *for* it.
   - **Lightweight**: a binary + systemd unit (or one small container), installable as a single
     task file in `addons/tasks/<name>.yml` — not a role, not a compose stack.
   - **No public web UI of its own.** Nothing that needs nginx, certbot, a domain, or its own
     auth surface. (This is the criterion that bites: an agent *with* a web console — netdata,
     for example — is app-shaped even though it feels like an agent.)
   - **Multi-app benefit**: it makes sense in the `manyOf` UDF of several existing consuming
     apps, not just one.
   - Its configuration fits env vars / API keys, deliverable either at install time or via the
     post-first-login `/etc/profile.d/addons.sh` prompt pattern.
   **`new-app`** when it's deployed for its own sake: it has its own UI/API surface users visit,
   needs domain/SSL/auth, owns a data store. When in doubt between the two, record both scores
   and STOP — the operator decides.
   - **Single-app enhancement ≠ addon ≠ new-app.** If the capability benefits **only one existing
     app** (e.g. "pre-install the LangChain SDKs in code-server"), it is a *change to that app* —
     verdict `already-exists`, routed as "scope a change to `apps/linode-marketplace-<x>`." It is
     **not** a shared `addons/` addon (that role is cross-app and observability-shaped — wiring a
     single-app option into it pollutes ~30 unrelated apps' `add_ons` UDFs), and it is **not** a
     new app (it duplicates the host app's whole playbook for a small delta). The `addon` verdict
     requires the *multi-app benefit* criterion above; one consumer fails it.
13. If `new-app`, classify its archetype bucket via `.claude/shared/reference-apps.md` (install
   method, web/proxy, auth model, GPU?/DB?/PHP?) so `/newapp-start` or `/backport-start` inherits
   the classification instead of re-deriving it.

### Phase 0e — Write the verdict
14. Write `.documentation/<app>/vetting.md`:
    - **Verdict** (one of the five) + one-paragraph rationale.
    - **Evidence table** — each claim with its citation (doc URL / `file:line @ SHA` / command
      + output).
    - **Provider landscape table** (0c) — per-provider offering + shape, with listing URLs, and
      the fit implication drawn from it.
    - **Rubric scoring** (0d) when app-vs-addon was in play.
    - **Taxonomy bucket** + the legacy-StackScript finding, when verdict is `new-app`.
    - **Deployable sibling** (name + URL), when verdict is `not-deployable-as-named`.
    - **OSS-equivalent alternative** (name + repo/docs URL), when the candidate was blocked and a
      self-hostable equivalent exists (per 0b step 8).
    - **OPEN QUESTIONS**, if any.
15. Do **not** initialize `STATE.md` — that belongs to the `:start` skills (or `/addon-build`),
    which read `vetting.md` and carry the verdict forward.

## Output
- `.documentation/<app>/vetting.md` — the cited verdict (this command owns it).
- A short operator summary: the verdict, the single strongest piece of evidence, and the exact
  next command to run (with arguments pre-filled, e.g. `/newapp-start <app> --repo <url>`).

## STOP — manual review (checkpoint)
Before the next command, the operator verifies:
- [ ] The verdict is one of the five, and every claim in `vetting.md` carries a real citation.
- [ ] The existence check was done against live `ls apps/` output, not the taxonomy alone.
- [ ] The provider landscape covers at least AWS/Azure/GCP marketplaces + the vendor's own
      deploy page, each offering classified by shape (one-click VM / vendor SaaS listing /
      managed service / tutorial-only), with "none found" recorded where applicable.
- [ ] If `addon`: all five rubric criteria are individually evidenced (especially *no own web UI*).
- [ ] If `not-deployable-as-named`: the deployable sibling (if any) is named with a URL.
- [ ] **Deployable ≠ wrappable**: a dev-environment/IDE-shell candidate was tested against "what
      does the box DO on its own?" — not waved through just because it has a UI.
- [ ] If blocked (`not-deployable-as-named` / `not-suitable`): an OSS-equivalent search was run and
      any alternative named with a URL (don't dead-end a blocked name).
- [ ] OPEN QUESTIONS are resolved or consciously deferred.

**Next:** depends on verdict — `/newapp-start` / `/backport-start` / `/addon-build` / STOP.
