# Setup Cloud Manager Development Environment

Bootstrap a local development environment for [`linode/manager`](https://github.com/linode/manager)
(the Cloud Manager monorepo), following its official `docs/GETTING_STARTED.md`: fork + clone, Volta
toolchain, OAuth client, `.env`, `pnpm bootstrap`, and a running dev server at
`http://localhost:3000`. The team makes Cloud Manager PRs from time to time; this gets a machine
from zero to contributing.

## Usage

```bash
/setup-cloud-manager-dev [options]
```

## Arguments

- `--oauth-id <id>` — OAuth client ID already created; skip the OAuth walkthrough (Phase 3) and write it into `.env` directly.
- `--skip-oauth` — Skip OAuth entirely; leave `REACT_APP_CLIENT_ID` commented in `.env`. The app builds and serves, but login won't work until the ID is set.
- `--minimal` — Stop after Phase 5 (bootstrap); skip the dev-server validation phase. For CI-ish or build-only setups.
- `--fork-url <url>` — Clone this fork instead of detecting/prompting for one.
- `--workspace <path>` — Parent directory for the clone (default `~/cloud-manager-dev`).

## Ground Rules

- **Re-verify before trusting this file.** The version pins and commands below were verified against
  the manager repo on 2026-06-12 (commit `c22c2026`, `develop`) and WILL drift. As soon as the repo
  is cloned (Phase 1), cross-check against its own `docs/GETTING_STARTED.md`, `.nvmrc`, and root
  `package.json` (`volta` field, `scripts`). On any mismatch, prefer the repo's values and tell the
  user this file needs updating. A possibly-stale offline reference clone may exist at
  `marketplace-apps/.reference/manager`.
- **Never push to GitHub.** Cloning, fetching, and local branches only — committing/pushing/opening
  PRs is always a manual operator step (team rule).
- **Don't clobber existing state.** If the workspace, clone, Volta, or an `.env` already exists,
  inspect it and reuse/report rather than overwrite. Ask before replacing anything.

## Process

### Phase 0 — Preflight

1. Confirm `git` and `curl` are installed (`command -v git curl`). These are hard requirements.
2. Report what's already present: `volta --version`, `node --version`, `pnpm --version` (each may be
   absent — that's fine, Phase 2 installs them).
3. Resource check — warn, don't hard-fail:
   - Disk: ≥ 10 GB free on the workspace volume (`df -h <workspace>`).
   - RAM: ≥ 8 GB (16 GB recommended). macOS: `sysctl -n hw.memsize`; Linux: `free -g`.

### Phase 1 — Repository

1. Resolve the fork to clone, in order:
   - `--fork-url` if given.
   - If `gh` CLI is installed and authed (`gh auth status`): offer to run
     `gh repo fork linode/manager --clone=true` inside the workspace (forks under the user's
     account if needed, clones, and wires `upstream` automatically).
   - Otherwise: tell the user to fork https://github.com/linode/manager in the browser, then ask
     for their fork's clone URL.
2. Create the workspace (`mkdir -p <workspace>`, default `~/cloud-manager-dev`) and clone:
   ```bash
   cd <workspace>
   git clone <fork-url> manager
   cd manager
   git remote add upstream https://github.com/linode/manager.git   # skip if gh already added it
   git fetch upstream
   git checkout develop
   ```
3. Now apply the ground rule: read the cloned repo's `docs/GETTING_STARTED.md`, `.nvmrc`, and root
   `package.json`, and reconcile every version/command in the phases below against them.

### Phase 2 — Toolchain

Per `GETTING_STARTED.md`, the repo pins Node via Volta (`.nvmrc`: `20.17`; root `package.json`
`volta` field: `20.17.0`) and uses pnpm v10.

1. Install Volta only if missing (this is the upstream-documented method):
   ```bash
   command -v volta || curl https://get.volta.sh | bash
   # Volta edits the shell rc; source it or remind the user to open a new terminal.
   ```
2. Install the pinned toolchain (substitute the versions read from the repo in Phase 1.3):
   ```bash
   volta install node@20.17
   volta install pnpm@10
   ```
3. Verify: `node --version` reports `v20.17.x` and `pnpm --version` reports `10.x`. If the shell
   still resolves an old Node, the rc wasn't sourced — fix that before continuing.

### Phase 3 — OAuth Client (manual browser step)

Skipped when `--oauth-id` was given; deferred (with a warning) when `--skip-oauth`.

Claude cannot do this part — walk the user through it and wait for the ID:

1. Open https://cloud.linode.com/profile/clients (any Linode account works) → **Add an OAuth App**.
2. Label: anything (e.g. `cm-local-dev`). Callback URL: exactly
   `http://localhost:3000/oauth/callback`.
3. Check the **Public** checkbox. Create.
4. Copy the **ID** — the client *secret* is not used for a public client.

### Phase 4 — Environment File

1. ```bash
   cp packages/manager/.env.example packages/manager/.env
   ```
2. In `packages/manager/.env`, uncomment and set:
   ```env
   REACT_APP_CLIENT_ID='<id from Phase 3>'
   ```
   and confirm the other required vars match the example defaults:
   ```env
   REACT_APP_LOGIN_ROOT='https://login.linode.com'
   REACT_APP_API_ROOT='https://api.linode.com/v4'
   REACT_APP_APP_ROOT='http://localhost:3000'
   ```
3. `.env` is gitignored upstream — confirm it stays untracked (`git status`). Never commit it.

### Phase 5 — Bootstrap

From the repo root:

```bash
pnpm bootstrap
```

This is the documented sequence (`install:all` → `build:validation` → `build:sdk`): installs all
workspace deps against the frozen lockfile, then builds `@linode/validation` and `@linode/api-v4`,
which the manager app imports. If it fails, read the actual error and fix the cause — don't retry
blindly, and don't substitute a bare `pnpm install` (it skips the package builds).

**Stop here if `--minimal`.** Report what was set up and how to run Phase 6 manually later.

### Phase 6 — Validate

1. Start the dev server in the background from the repo root: `pnpm dev` (runs api-v4, validation,
   ui, utilities, queries, shared, and manager concurrently).
2. Poll `http://localhost:3000` until it returns HTML (allow a couple of minutes for the first
   Vite build).
3. Tell the user to open `http://localhost:3000` and log in — the OAuth redirect through
   `login.linode.com` must be completed by a human in the browser.
4. On success, report: server running, how to stop it (kill the `pnpm dev` process), and that
   `pnpm start:manager` exists as a lighter manager-only alternative.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `volta: command not found` right after install | Shell rc not sourced — open a new terminal or `source ~/.zshrc` |
| Wrong Node version despite Volta | Another Node on PATH ahead of Volta's shims; check `which -a node` |
| Port 3000 already in use | `lsof -i :3000`, stop the other process, or change `REACT_APP_APP_ROOT` *and* the OAuth callback to match |
| Login loops or "redirect URI mismatch" | Callback URL isn't exactly `http://localhost:3000/oauth/callback`, or the OAuth app isn't **Public** |
| Manager fails to resolve `@linode/api-v4` / `@linode/validation` | Packages weren't built — run `pnpm bootstrap`, not bare `pnpm install` |

## After Setup — Contributing

From the repo's `docs/CONTRIBUTING.md` (verify there, it's authoritative):

- Branch from `develop`: `git checkout develop && git pull && git checkout -b <branch>`.
- Commit / PR title format: `<type>: [M3-XXXX] - <description>` where type ∈
  `feat | fix | change | refactor | test | upcoming`.
- PRs target `develop`; CI must pass; two Cloud Manager team reviews; squash merge.
- Add a changelog entry with `pnpm changeset` when the change is user-facing.
- Useful while developing: `pnpm test:manager` (Vitest), `pnpm storybook` (port 6006),
  `pnpm cy:e2e` (Cypress — needs a `MANAGER_OAUTH` personal access token and **creates/deletes real
  resources** on the account; use a test account).

The operator commits and pushes — Claude never does.
