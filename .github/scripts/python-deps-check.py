import json
import os
import re
import urllib.request
from pathlib import Path


def get_latest_version(package: str) -> str | None:
    try:
        url = f'https://pypi.org/pypi/{package}/json'
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.load(r)['info']['version']
    except Exception:
        return None


def get_current_versions(requirement_file: Path) -> dict[str, str]:
    current_versions = {}
    for line in requirement_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        package = re.match(r'^([A-Za-z0-9_\-\.]+)==(.+)$', line)
        if package:
            pkg_name = package[1]
            pkg_version = package[2]
            current_versions[pkg_name] = pkg_version
    return current_versions


def main():
    print('Getting list of apps requirement files...')
    repo_root = Path(__file__).parent.parent.parent
    requirement_files = sorted((repo_root / 'apps').rglob('requirements.txt'))

    print('Getting unique list of packages...')
    all_packages: set[str] = set()
    for requirement_file in requirement_files:
        for pkg_name, _ in get_current_versions(requirement_file).items():
            all_packages.add(pkg_name)

    print(f'Getting latest packages versions from PyPI...')
    latest_versions: dict[str, str] = {}
    for pkg_name in all_packages:
        version = get_latest_version(pkg_name)
        if version:
            latest_versions[pkg_name] = version

    print(f'Checking and updating package versions...')
    report = []
    for requirement_file in requirement_files:
        app = requirement_file.parts[6]
        pinned = get_current_versions(requirement_file)
        content = requirement_file.read_text()
        changed = False

        for pkg_name, pkg_version in pinned.items():
            new = latest_versions.get(pkg_name)
            if not new or new == pkg_version:
                continue
            content = content.replace(f'{pkg_name}=={pkg_version}', f'{pkg_name}=={new}')
            report.append(f'| `{app}` | `{pkg_name}` | `{pkg_version}` | `{new}` |')
            changed = True

        if changed:
            requirement_file.write_text(content)

    any_updates = bool(report)

    print('Creating PR body content...')
    body = (
        '## Python Dependency Updates\n\n'
        '| App | Package | Current | Latest |\n'
        '|-----|---------|---------|--------|\n'
        + '\n'.join(report)
    )
    Path('/tmp/pr_body.md').write_text(body)

    output = os.environ.get('GITHUB_OUTPUT', '/dev/null')
    with open(output, 'a') as f:
        f.write(f'any_updates={"true" if any_updates else "false"}\n')


if __name__ == '__main__':
    main()

