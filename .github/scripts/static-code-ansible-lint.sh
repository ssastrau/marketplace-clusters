#!/usr/bin/env bash

set -e

if [ -n "$CONFIGS" ]; then
	APP_DIRS=$(echo "$CONFIGS" | jq -r '.[] | "apps/" + .' | tr '\n' ' ')
	LINT_PATHS=$(find $APP_DIRS -type f \( -name '*.yml' -o -name '*.yaml' \) | tr '\n' ' ')
	echo "Linting updated apps: $APP_DIRS"
else
	LINT_PATHS=""
	echo "Linting all apps"
fi

pip install ansible-lint
ansible-galaxy collection install community.general community.docker community.crypto linode.cloud ansible.posix gluster.gluster community.mysql community.postgresql
export ANSIBLE_CONFIG="tests/static_code_analysis/ansible_playbooks/ansible.cfg"
ansible-lint -c tests/static_code_analysis/ansible_playbooks/.ansible-lint.yaml $LINT_PATHS
echo "✅ ansible-lint passed: no errors found."
