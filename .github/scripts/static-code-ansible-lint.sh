#!/usr/bin/env bash

set -e

if [ -n "$CONFIGS" ]; then
	APP_DIRS=$(echo "$CONFIGS" | jq -r '.[] | select(. != "linode_helpers") | "apps/" + .' | tr '\n' ' ')
	if [ -n "$APP_DIRS" ]; then
		LINT_PATHS=$(find $APP_DIRS -type f \( -name '*.yml' -o -name '*.yaml' \) | tr '\n' ' ')
		echo "Linting updated apps: $APP_DIRS"
	else
		LINT_PATHS=""
		echo "No apps to lint."
		exit 0
	fi
else
	LINT_PATHS=""
	echo "Linting all apps"
fi

echo "::group::pip install ansible-lint"
time pip install ansible-lint
echo "::endgroup::"

echo "::group::ansible-galaxy collection install"
time ansible-galaxy collection install community.general community.docker community.crypto linode.cloud ansible.posix gluster.gluster community.mysql community.postgresql
echo "::endgroup::"

export ANSIBLE_CONFIG="tests/static_code_analysis/ansible_playbooks/ansible.cfg"

echo "::group::ansible-lint"
time ansible-lint -c tests/static_code_analysis/ansible_playbooks/.ansible-lint.yaml $LINT_PATHS
echo "::endgroup::"

echo "✅ ansible-lint passed: no errors found."
