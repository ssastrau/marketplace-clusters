# Running this workflow in GitHub Copilot CLI

This pipeline was built as Claude Code skills, but **GitHub Copilot CLI runs the exact same
skills** — no port, no duplicate copies. `.claude/` stays the single source of truth (maintained
via Claude Code); Copilot reads it natively. This lets you test both tools side by side against
one skill set.

## Why no duplication is needed

Copilot CLI discovers **project skills** from `.github/skills`, `.claude/skills`, **or**
`.agents/skills` in the repo ([docs](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills)).
Because our skills already live in `.claude/skills/<name>/SKILL.md`, Copilot loads all of them
directly. The Claude-only frontmatter keys (`disable-model-invocation`, `arguments`) are simply
ignored by Copilot; the skill **name** is inferred from the directory. Verify with:

```bash
copilot skill list        # from inside marketplace-apps
```

You should see every pipeline phase: `app-vet`, `backport-start`, `newapp-start`,
`app-manual-install`, `app-ansibilize`, `app-deploy`, `validate-config`,
`ui-regression-tests`, `app-pr`, `addon-build`, plus `setup-cloud-manager-dev`.

## Invoking skills — Claude vs Copilot

| | Claude Code | Copilot CLI |
|---|---|---|
| Invoke a phase | `/app-vet <app> --repo <url>` | `use the app-vet skill on <app> (repo <url>)`, or `/app-vet` in-session |
| List skills | `/skills` | `copilot skill list` / `/skills` |
| Skill details | — | `/skills info <name>` |
| Reload after edit | restart | `/skills reload` |

Arguments: Claude parses positional/flag args from the slash command. In Copilot, state them in
the prompt ("...on nomad, instance 172.x.x.x") — each SKILL.md already explains how it reads
`$ARGUMENTS`.

## Instructions

Copilot loads, in-repo, **all** of: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, plus
`~/.copilot/copilot-instructions.md` (personal, durable prefs only). The marketplace standards
in `CLAUDE.md` therefore apply in Copilot with no extra setup. **Do not run `/init`** — it would
generate a redundant `AGENTS.md` and risk clobbering the curated files.

## Linode MCP setup (one-time, per machine)

The deploy/manual-install skills drive Linode via the `linode-team` / `linode-personal` MCP
servers (the `linode-mcp` Python server). To make them available in Copilot:

1. Ensure `~/.copilot/mcp-config.json` defines both servers as `stdio`, launched with
   `uv run --directory <path-to>/linode-mcp python server.py`, each mapping `LINODE_API_TOKEN`
   to a `${...}` env reference:

   ```json
   {
     "mcpServers": {
       "linode-team": {
         "type": "stdio",
         "command": "uv",
         "args": ["run","--directory","<path>/linode-mcp","python","server.py"],
         "env": { "LINODE_API_TOKEN": "${LINODE_TEAM_TOKEN}" },
         "tools": ["*"]
       },
       "linode-personal": { "... same, LINODE_API_TOKEN": "${LINODE_PERSONAL_TOKEN}" }
     }
   }
   ```

2. Export the tokens in your shell profile (e.g. `~/.zshrc`) — **never** commit them or put the
   literal token in the config file:

   ```bash
   export LINODE_TEAM_TOKEN=...       # Cloud Manager token, team account
   export LINODE_PERSONAL_TOKEN=...   # personal account
   ```

3. Open a new terminal (so the exports load) and confirm with `/mcp`. Per team convention, use
   `linode-team` for work resources.

> If the MCP server fails to start, the usual cause is an **unset token env var** — `${VAR}`
> then expands to empty. Check the vars are exported in the shell that launched Copilot.

## Known differences to keep in mind

- **No `disable-model-invocation` equivalent.** In Claude these skills never auto-trigger; in
  Copilot the model *may* choose a skill based on its description. The descriptions say
  "User-invoked only," which strongly discourages it, but treat auto-invocation as possible.
- **Commands must be top-level or skills.** Copilot only picked up top-level `.claude/commands/*.md`,
  not nested ones — which is why Phase-5 `validate-config` was converted from a nested command
  into a proper `.claude/skills/validate-config/` skill (works in both tools).
- **Same standing rules apply** (grounding/no-hallucination, never push to GitHub, README last,
  STOP checkpoints) — they come from `CLAUDE.md` and the skills themselves, which both tools read.
