#!/bin/bash
# Checks all requirements.txt files across apps for outdated packages.
# Outputs a JSON file mapping each app to its list of outdated packages.
# Usage: bash .github/scripts/python-deps-check.sh
# Outputs: /tmp/outdated.json

set -euo pipefail

# Initialise empty report
echo "{}" > /tmp/outdated.json

for req_file in $(find apps -name "requirements.txt" | sort); do
  app=$(echo "$req_file" | cut -d'/' -f2)
  echo "::group::Checking ${app}"

  python3 -m venv /tmp/venv_check
  /tmp/venv_check/bin/pip install --quiet --upgrade pip

  # Install only active (non-commented) packages; tolerate failures (some may not resolve on this OS)
  grep -v '^\s*#' "$req_file" | grep -v '^\s*$' \
    | /tmp/venv_check/bin/pip install --quiet -r /dev/stdin || true

  # Write pip outdated JSON to a temp file — avoids any shell quoting issues
  /tmp/venv_check/bin/pip list --outdated --format=json 2>/dev/null \
    > /tmp/pip_outdated.json || echo "[]" > /tmp/pip_outdated.json

  rm -rf /tmp/venv_check

  # Filter to only packages pinned in this requirements.txt, then merge into report
  python3 << PYEOF
import json, re, sys

req_file = "${req_file}"
app      = "${app}"

def normalise(name):
    return re.sub(r'[-_.]', '-', name.strip().lower())

# Parse pinned packages from requirements.txt
pinned = {}
with open(req_file) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = re.match(r'^([A-Za-z0-9_\-\.]+)==(.+)$', line)
        if m:
            pinned[normalise(m.group(1))] = m.group(2).strip()

# Load what pip considers outdated
with open('/tmp/pip_outdated.json') as f:
    try:
        outdated_all = json.load(f)
    except json.JSONDecodeError:
        outdated_all = []

# Keep only those that are in this requirements.txt
filtered = []
for pkg in outdated_all:
    key = normalise(pkg['name'])
    if key in pinned:
        filtered.append({
            'name': pkg['name'],
            'current': pinned[key],
            'latest': pkg['latest_version'],
        })

if filtered:
    print(f"  Found {len(filtered)} update(s) for {app}")
else:
    print(f"  All pinned packages up to date for {app}")

# Merge into the shared report
with open('/tmp/outdated.json') as f:
    report = json.load(f)

report[app] = filtered

with open('/tmp/outdated.json', 'w') as f:
    json.dump(report, f, indent=2)
PYEOF

  echo "::endgroup::"
done

echo "Outdated dependency report:"
cat /tmp/outdated.json

