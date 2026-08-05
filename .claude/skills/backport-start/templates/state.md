# Workflow State — <app>

- app: <app>
- type: backport | newapp
- branch: add/<app>-backport
- stackscript_legacy: <id | n/a>     # backport only — the legacy SS introspected by /backport-start
- stackscript_deploy: <id | n/a>     # created by /app-deploy
- manual_install_box: { id: <>, ip: <>, rdns: <>, root_pw_in_credentials: <yes/no> }
- fresh_deploy_box:   { id: <>, ip: <> }
- credentials: /home/<user>/.credentials
- upstream_clone: .reference/<repo> @ <commit-sha>   # gitignored; SHA pins the citations

## Phases
- [ ] vet (optional)       -> vetting.md   # /app-vet Phase 0 — verdict + taxonomy bucket, if run
- [ ] research/analyze     -> architecture_decisions.md
- [ ] manual-install       -> manual_install.md
- [ ] ansibilize           -> apps/linode-marketplace-<app>/ + deployment_scripts/...
- [ ] deploy               -> e2e_testing.md
- [ ] validate-config      -> validation_findings.md
- [ ] ui-regression-tests  -> ui_testing.md + tests/regression_tests/
- [ ] pr                   -> README.md + PR

## Next step
<command to run next>

## Checkpoint (must pass before next step)
<what the operator verifies>

## Open questions
<ungroundable facts awaiting empirical resolution — block the next phase until resolved or consciously deferred>

## Log
- <YYYY-MM-DD> <event>
