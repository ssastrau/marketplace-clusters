#!/bin/bash
# Checks all requirements.txt files across apps for outdated packages.
# Outputs a JSON file mapping each app to its list of outdated packages.
# Usage: bash .github/scripts/python-deps-check.sh
# Outputs: /tmp/outdated.json

set -euo pipefail

OUTDATED_JSON="{}"

for req_file in $(find apps -name "requirements.txt" | sort); do
  app=$(echo "$req_file" | cut -d'/' -f2)
  echo "::group::Checking ${app}"

  python -m venv /tmp/venv_check
  /tmp/venv_check/bin/pip install --quiet --upgrade pip

  # Install only active (non-commented) packages
  grep -v '^\s*#' "$req_file" | grep -v '^\s*$' \
    | /tmp/venv_check/bin/pip install --quiet -r /dev/stdin || true

  # Get outdated packages as JSON array: [{name, version, latest_version}]
  APP_OUTDATED=$(/tmp/venv_check/bin/pip list --outdated --format=json 2>/dev/null || echo "[]")

  rm -rf /tmp/venv_check

  COUNT=$(echo "$APP_OUTDATED" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
  if [ "$COUNT" -eq 0 ]; then
    echo "All packages up to date for ${app}"
    echo "::endgroup::"
    continue
  fi

  echo "Found ${COUNT} outdated package(s) for ${app}"

  # Filter: only include packages that are actually pinned in this requirements.txt
  FILTERED=$(echo "$APP_OUTDATED" | python3 - <<PYEOF "$req_file"
import sys, json, re

req_file = sys.argv[1]
with open(req_file) as f:
    lines = f.readlines()

# Build a set of pinned package names (normalised: lowercase, - and _ equivalent)
def normalise(name):
    return re.sub(r'[-_.]', '-', name.strip().lower())

pinned = {}
for line in lines:
    line = line.strip()
    if line.startswith('#') or not line:
        continue
    m = re.match(r'^([A-Za-z0-9_\-\.]+)==(.+)$', line)
    if m:
        pinned[normalise(m.group(1))] = m.group(2)

data = json.load(sys.stdin)
result = []
for pkg in data:
    if normalise(pkg['name']) in pinned:
        result.append({
            'name': pkg['name'],
            'current': pinned[normalise(pkg['name'])],
            'latest': pkg['latest_version']
        })

print(json.dumps(result))
PYEOF
  )

  OUTDATED_JSON=$(echo "$OUTDATED_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
data['${app}'] = json.loads('''${FILTERED}''')
print(json.dumps(data))
")

  echo "::endgroup::"
done

echo "$OUTDATED_JSON" > /tmp/outdated.json
echo "Wrote outdated dependency report to /tmp/outdated.json"
cat /tmp/outdated.json

