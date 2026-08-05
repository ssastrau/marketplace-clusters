# Workflow State — addon: <addon>

- addon: <addon>
- type: addon
- branch: add/<addon>-addon
- vetting: .documentation/<addon>/vetting.md | operator decision (<date>)
- upstream_clone: .reference/<repo> @ <commit-sha>   # gitignored; SHA pins the citations
- manual_install_box: { id: <>, ip: <>, root_pw_in_credentials: <yes/no> }
- pilot_apps: [<app1>, <app2>]                       # operator's Stage-3 rollout decision
- stackscript_deploy: <id | n/a>                     # per pilot app, created in Stage 4
- pilot_boxes: [{ app: <>, id: <>, ip: <> }]

## Stages
- [ ] manual-install   -> manual_install.md
- [ ] ansibilize       -> apps/linode_helpers/roles/addons/tasks/<addon>.yml + main.yml entry
- [ ] wire-udfs        -> pilot deployment_scripts manyOf= updates (rollout decision recorded)
- [ ] deploy-test      -> e2e_testing.md (addon smoke + host-app smoke + control deploy)
- [ ] pr               -> linode_helpers README update + pr_description.md

## Next step
<command / stage to run next>

## Checkpoint (must pass before next stage)
<what the operator verifies>

## Open questions
<ungroundable facts awaiting empirical resolution — block the next stage until resolved or consciously deferred>

## Log
- <YYYY-MM-DD> <event>
