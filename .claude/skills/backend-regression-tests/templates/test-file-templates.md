# Code Templates

Copy these templates when generating backend test files. Replace every `{placeholder}` with real
values from the live probe (Step 5). Backend tests are **SSH- and HTTP-driven** — they never use a
browser, never import Playwright, and never request the `context` / `browser` fixtures.

---

## Shared infra — add ONCE, reuse forever

The first backend app the suite ever gets needs this plumbing added to the **shared, tracked** files.
Every later backend app **reuses it untouched** — never redefine it per app. If it's already present,
skip straight to the app-specific files below.

### `services/__init__.py` — create the package (empty file)

Add an empty `tests/regression_tests/services/__init__.py` the first time — the package-level init
that makes `regression_tests.services.*` importable, the counterpart of the existing
`pages/__init__.py`. Without it, every SOM import fails at collection. (Each app also gets its own
`services/{pkg}/__init__.py`.)

### `utils/ssh.py` — add `run_remote_command`

Built on the existing `ssh_connection` context manager already in that file.

```python
def run_remote_command(host: str, username: str, password: str, command: str,
                       timeout: int = 30) -> tuple[str, str, int]:
    """
    Runs a single command on the remote Linode over SSH and returns its result.

    Args:
        host, username, password: SSH credentials (from the ssh_credentials fixture).
        command: The command to execute on the VM.
        timeout: Command timeout in seconds.

    Returns:
        tuple[str, str, int]: (stdout, stderr, exit_code), stdout/stderr stripped.
    """
    with ssh_connection(host, username, password, timeout=timeout) as client:
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        return out, err, exit_code
```

### global `conftest.py` — add `remote_exec` and `http_session`

```python
import requests
from regression_tests.utils.ssh import run_remote_command


@pytest.fixture(scope="session")
def remote_exec(ssh_credentials):
    """
    Returns a callable that runs a command on the deployed VM over SSH.
    The backbone of backend tests: headless services are often loopback-bound or
    firewalled, so their client commands run ON the box, not from the test runner.

    Usage in a test/service:
        out, err, code = remote_exec("redis-cli ping")

    Returns:
        Callable[[str, int], tuple[str, str, int]] -> (stdout, stderr, exit_code).
    """
    host, username, password = ssh_credentials

    def _run(command: str, timeout: int = 30) -> tuple[str, str, int]:
        return run_remote_command(host, username, password, command, timeout=timeout)

    return _run


@pytest.fixture(scope="session")
def http_session():
    """
    Returns a requests.Session for apps that expose an HTTP API. verify=False because
    test deploys use self-signed *.ip.linodeusercontent.com certs. Use only for
    endpoints that are genuinely public; loopback/firewalled endpoints are reached with
    `curl` over `remote_exec` instead.

    Yields:
        requests.Session
    """
    session = requests.Session()
    session.verify = False
    yield session
    session.close()
```

> Adding these edits the shared suite the UI tests also depend on — it's a deliberate, reviewed
> footprint (on the SKILL.md manual-review checklist). Do not duplicate them into an app conftest.

---

## app `conftest.py`

`credentials_file_path` is needed whenever the app has a credentials file. `base_url` is needed
**only when the app exposes an HTTP API** (`App URL:` present in `/etc/motd`); a pure
SSH-only service (a firewalled DB with no HTTP surface) omits `base_url` entirely.

```python
import pytest


@pytest.fixture(scope="session")
def credentials_file_path():
    """
    Returns the path to the credentials file on the remote {App} server.

    Returns:
        str: Absolute path to the credentials file.
    """
    return "/home/admin/.credentials"    # use the exact path from 'Credentials File:' in /etc/motd


# --- Include base_url ONLY if the app has an HTTP API (App URL: in /etc/motd). Omit for SSH-only services. ---
@pytest.fixture(scope="session")
def base_url(ssh_credentials) -> str:
    """
    Returns the base URL for the {App} HTTP API.
    Built from the VM host so the suite works against any freshly deployed instance.

    Returns:
        str: The base URL of the {App} API.
    """
    host = ssh_credentials[0]
    linode_host = host.replace(".", "-")
    return f"https://{linode_host}.ip.linodeusercontent.com"  # append :port / path if 'App URL:' has one
```

Derive `base_url` from the VM host — **do not** hardcode the URL string, or the suite breaks on the
next deployment. Match the `App URL:` from `/etc/motd` by appending a port and/or path suffix when
present.

---

## Repeated-key credentials (only when the credentials file repeats a key name)

`app_credentials` parses the file into a flat dict, so a repeated key keeps only the **last** value.
When the login key you need isn't the last occurrence, add a targeted fixture to the app conftest —
do **not** redefine the global `app_credentials`.

```python
import re
import pytest
from regression_tests.utils.ssh import ssh_connection


@pytest.fixture(scope="session")
def {pkg}_credentials(ssh_credentials, credentials_file_path) -> dict:
    """
    Extracts the intended {App} account from a credentials file that repeats key names.
    Anchors on the specific account instead of relying on flat last-wins parsing.
    """
    host, username, password = ssh_credentials
    with ssh_connection(host, username, password) as client:
        _, stdout, _ = client.exec_command(f"cat {credentials_file_path}")
        content = stdout.read().decode()
    # Anchor on the literal account, then capture its adjacent secret line:
    m = re.search(r"admin.*?password:\s*'([^']+)'", content, re.DOTALL | re.IGNORECASE)
    return {"username": "admin", "password": m.group(1)}
```

---

## Service class (SOM — the backend analog of a Page Object)

Service objects hold client / CLI / API **actions** and return raw results. **No assertions** — those
live in the test functions. A method runs each command through the injected `remote_exec` (fresh SSH
per call) or hits the API through `http_session`.

### SSH-driven service (DB / cache / VPN / broker CLI)

```python
class {App}Service:
    """Client actions for {App}, executed on the VM over SSH. No assertions here."""

    UNIT = "{unit_name}"    # exact unit from `systemctl is-active` in Step 5

    def __init__(self, remote_exec):
        self._run = remote_exec

    def is_active(self) -> str:
        # `systemctl is-active` prints "active" and exits 0 when the unit is running.
        out, _, _ = self._run(f"systemctl is-active {self.UNIT}")
        return out

    def listening_ports(self) -> str:
        # Raw `ss` output; the test asserts the bind address + port it saw in Step 5.
        out, _, _ = self._run("ss -tlnH")
        return out

    def ping(self, password: str) -> str:
        # Example client action (redis). Replace with the real Step-5 command for this app.
        out, _, _ = self._run(f"redis-cli -a {password} --no-auth-warning ping")
        return out

    def set_get(self, password: str, key: str, value: str) -> str:
        self._run(f"redis-cli -a {password} --no-auth-warning set {key} {value}")
        out, _, _ = self._run(f"redis-cli -a {password} --no-auth-warning get {key}")
        return out
```

### HTTP-driven service (API app — vector store, LLM, exporter)

```python
class {App}Service:
    """API actions for {App} over HTTP. No assertions here."""

    def __init__(self, http_session, base_url: str):
        self._http = http_session
        self._base = base_url.rstrip("/")

    def ready(self):
        # Returns the raw response; the test asserts status/body it saw in Step 5.
        return self._http.get(f"{self._base}/v1/.well-known/ready", timeout=30)

    def version(self):
        return self._http.get(f"{self._base}/api/version", timeout=30)
```

For a **loopback/firewalled** API, don't use `http_session` — reach it with `curl` over
`remote_exec` instead (so it runs on the box):

```python
    def heartbeat_local(self, remote_exec) -> str:
        out, _, _ = remote_exec("curl -sk http://127.0.0.1:8000/api/v1/heartbeat")
        return out
```

---

## test_scenarios.py

The baseline (`test_{pkg}_service_active`, plus a port test when there's a port worth asserting) is
always generated. Everything else comes from the confirmed scenarios. Every `assert` carries a
failure message.

### SSH-driven app (DB / cache / VPN)

```python
from regression_tests.services.{pkg}.{pkg}_service import {App}Service


def test_{pkg}_service_active(remote_exec):
    # Verifies that the {App} systemd unit is running.
    service = {App}Service(remote_exec)
    assert service.is_active() == "active", "{App} unit is not active"


def test_{pkg}_port_listening(remote_exec):
    # Verifies that {App} binds its port on the expected address.
    service = {App}Service(remote_exec)
    ports = service.listening_ports()
    # Loopback-only bind is the CORRECT posture for a firewalled datastore — assert it as seen.
    assert "127.0.0.1:{port}" in ports, "{App} is not listening on 127.0.0.1:{port}"


def test_{pkg}_ping(remote_exec, app_credentials):
    # Verifies that {App} answers its client with valid credentials.
    password = app_credentials["Exact Password Key"]   # key name from Step 4
    service = {App}Service(remote_exec)
    assert service.ping(password) == "PONG", "{App} did not answer PING"


def test_{pkg}_set_get_roundtrip(remote_exec, app_credentials):
    # Verifies that a write then read returns the stored value.
    password = app_credentials["Exact Password Key"]
    service = {App}Service(remote_exec)
    assert service.set_get(password, "regression_key", "regression_value") == "regression_value", \
        "{App} did not return the value that was written"
```

### DB query example (postgres / pgvector)

```python
def test_{pkg}_select_one(remote_exec, app_credentials):
    # Verifies that the DB accepts auth and answers a trivial query.
    user = app_credentials["Exact User Key"]
    password = app_credentials["Exact Password Key"]
    out, _, code = remote_exec(
        f"PGPASSWORD='{password}' psql -h 127.0.0.1 -U {user} -tAc 'SELECT 1'"
    )
    assert code == 0, f"psql connection/auth failed: {out}"
    assert out.strip() == "1", f"unexpected query result: {out!r}"
```

### HTTP-driven app (public API)

```python
from regression_tests.services.{pkg}.{pkg}_service import {App}Service


def test_{pkg}_service_active(remote_exec):
    # Verifies that the {App} unit is running (the unit check stays over SSH even for an HTTP app).
    out, _, _ = remote_exec("systemctl is-active {unit_name}")
    assert out == "active", "{App} unit is not active"


def test_{pkg}_api_ready(http_session, base_url):
    # Verifies that the {App} readiness endpoint responds 200 (public endpoint only).
    service = {App}Service(http_session, base_url)
    response = service.ready()
    assert response.status_code == 200, f"readiness endpoint returned {response.status_code}"
```

---

## `backend_testing.md` artifact

The skill's per-app artifact (parallels `e2e_testing.md` / `ui_testing.md`): append a dated section
to `.documentation/{app}/backend_testing.md` — per-app working notes live under `.documentation/{app}/`
(gitignored, never synced). Get the date with `date '+%Y-%m-%d'`. Create the file if it doesn't exist;
append a new `##` section if it does (never overwrite an earlier run).

**No sensitive data.** Never write credentials, passwords, tokens, or credential-file contents into
the artifact. Credential *key names*, unit names, and port numbers are fine; their *values* and the
**base URL / API endpoint** are not.

````markdown
## {App} — backend regression test run ({YYYY-MM-DD})

### Scope
<one line — what was requested / scenarios covered, and where they came from (artifact vs. operator)>

### Discovered
- Unit: `{unit_name}` (active via `systemctl is-active`)
- Bind / firewall posture: <e.g. 127.0.0.1:6379 loopback-only — correct for a firewalled cache>
- Auth model: <credential key names used | none — no-auth loopback service>
- API endpoints (if any): <paths probed, vantage (public HTTP vs. curl-over-SSH) — NO base URL>
- Client commands: <the real Step-5 commands the tests assert on>

### Created
- Service object: `services/{pkg}/{pkg}_service.py`
- Tests: `test_{pkg}_service_active`, `test_{pkg}_port_listening`, `test_{pkg}_<scenario>`
- Shared infra added this run: <yes: remote_exec / http_session / run_remote_command | no — already present>

### Verified
- Boxes deployed (ids only): exploration <id>; final green run on fresh deploy <id>
- Suite type: <idempotent-only (verified in place) | one-time-state (proven on fresh redeploy)>

### Notes / issues
- <readiness races needing a wait, slow ops needing a longer timeout, ambiguous unit names, anything a future run should know>
- Troubleshooting entries added this session: <list | none>
````
