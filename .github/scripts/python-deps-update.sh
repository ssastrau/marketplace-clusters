#!/bin/bash
# Reads /tmp/outdated.json produced by python-deps-check.sh,
# updates all requirements.txt files in-place, and writes a PR body
# to /tmp/pr_body.md.
# Usage: bash .github/scripts/python-deps-update.sh
# Inputs:  /tmp/outdated.json
# Outputs: updated requirements.txt files, /tmp/pr_body.md

set -euo pipefail

if [ ! -f /tmp/outdated.json ]; then
  echo "ERROR: /tmp/outdated.json not found. Run python-deps-check.sh first."
  exit 1
fi

# Check if there is anything to update
TOTAL=$(python3 -c "
import json
data = json.load(open('/tmp/outdated.json'))
print(sum(len(v) for v in data.values()))
")

if [ "$TOTAL" -eq 0 ]; then
  echo "No outdated dependencies found. Nothing to update."
  echo "any_changes=false" >> "${GITHUB_OUTPUT:-/dev/null}"
  exit 0
fi

PR_BODY="## Python Dependency Updates\n\n"
PR_BODY+="Automated weekly dependency update — $(date +%Y-%m-%d)\n\n"
PR_BODY+="| App | Package | Current | Latest |\n"
PR_BODY+="|-----|---------|---------|--------|\n"

ANY_CHANGES=false

# Apply updates per app
python3 - <<'PYEOF'
import json, re, sys

data = json.load(open('/tmp/outdated.json'))

for app, packages in data.items():
    if not packages:
        continue

    req_file = f"apps/{app}/requirements.txt"

    with open(req_file) as f:
        content = f.read()

    for pkg in packages:
        name    = pkg['name']
        latest  = pkg['latest']

        # Match the package line case-insensitively, normalising - _ .
        pattern = re.compile(
            r'^(' + re.escape(name).replace(r'\-', r'[-_.]').replace(r'\_', r'[-_.]') + r')==[^\s]+',
            re.IGNORECASE | re.MULTILINE
        )

        if pattern.search(content):
            content = pattern.sub(lambda m: m.group(0).split('==')[0] + '==' + latest, content)
            print(f"  Updated {name} in {req_file} -> {latest}")

    with open(req_file, 'w') as f:
        f.write(content)

PYEOF

# Build PR body table from the JSON report
while IFS= read -r app; do
  PACKAGES=$(python3 -c "
import json
data = json.load(open('/tmp/outdated.json'))
pkgs = data.get('${app}', [])
for p in pkgs:
    print(p['name'], p['current'], p['latest'])
")
  if [ -n "$PACKAGES" ]; then
    while IFS=' ' read -r pkg current latest; do
      PR_BODY+="| \`${app}\` | \`${pkg}\` | \`${current}\` | \`${latest}\` |\n"
      ANY_CHANGES=true
    done <<< "$PACKAGES"
  fi
done < <(python3 -c "
import json
data = json.load(open('/tmp/outdated.json'))
for app in sorted(data):
    if data[app]:
        print(app)
")

printf "%b" "$PR_BODY" > /tmp/pr_body.md
echo "PR body written to /tmp/pr_body.md"

echo "any_changes=${ANY_CHANGES}" >> "${GITHUB_OUTPUT:-/dev/null}"

