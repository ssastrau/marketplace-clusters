# Code Templates

Copy these templates when generating test files. Replace every `{placeholder}` with real values
from the exploration step.

---

## conftest.py

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


@pytest.fixture(scope="session")
def base_url(ssh_credentials) -> str:
    """
    Returns the base URL for the {App} app.
    Built from the VM host so the suite works against any freshly deployed instance.

    Args:
        ssh_credentials: Tuple of (host, user, password) from env vars.

    Returns:
        str: The base URL of the {App} app.
    """
    host = ssh_credentials[0]
    linode_host = host.replace(".", "-")
    return f"https://{linode_host}.ip.linodeusercontent.com"  # append :port / path if 'App URL:' has one
```

Derive `base_url` from the VM host — **do not** hardcode the URL string, or the suite breaks on
the next deployment. Every app in the suite uses this `host.replace(".", "-")` form. Match the
`App URL:` from `/etc/motd` by appending a port and/or path suffix when present, e.g.
`...ip.linodeusercontent.com:3000/ui/panel`.

---

## HTTP Basic Auth (only when the app is behind htpasswd)

Add this fixture to the app's `conftest.py` to override the global `http_credentials` (which
returns `None`). The global `context` fixture forwards it to the browser context automatically —
no test changes needed.

```python
@pytest.fixture
def http_credentials(app_credentials) -> dict:
    """
    Provides HTTP Basic Auth credentials for the {App} browser context.
    Overrides the default (None) from the global conftest.
    """
    return {
        "username": app_credentials["Exact Username Key"],   # key name from Step 4
        "password": app_credentials["Exact Password Key"],   # key name from Step 4
    }
```

---

## Page class

```python
from playwright.sync_api import Page
from regression_tests.pages.base_page import BasePage


class {App}LoginPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.username_input = self.page.locator("#username")              # real selector from exploration
        self.password_input = self.page.locator("#password")              # real selector from exploration
        self.login_button   = self.page.locator("button[type='submit']")  # real selector from exploration

    def login(self, username: str, password: str):
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()
```

---

## test_scenarios.py

`test_{pkg}_login` (and the login page object it imports) applies **only when the app has a
login** — for a public, no-auth app generate the startup test alone; don't invent a login flow.

```python
from playwright.sync_api import expect

from regression_tests.pages.{pkg}.{pkg}_login_page import {App}LoginPage
from regression_tests.pages.{pkg}.{pkg}_{feature}_page import {App}{Feature}Page


def test_{pkg}_startup(context, base_url):
    # Verifies that the app started and the login page loads successfully.
    login_page = {App}LoginPage(context)
    login_page.navigate(base_url)
    expect(context, "{App} is not started").to_have_title("Exact Title From Exploration")
    expect(login_page.username_input, "Login form did not render.").to_be_visible()


def test_{pkg}_login(context, base_url, app_credentials):
    # Verifies that the user can log in with provided credentials.
    username = app_credentials["Exact Key From Credentials File"]   # key name from Step 4
    password = app_credentials["Exact Key From Credentials File"]   # key name from Step 4
    login_page = {App}LoginPage(context)
    login_page.navigate(base_url)
    login_page.login(username, password)
    dashboard_page = {App}{Feature}Page(context)
    expect(dashboard_page.some_element, "Dashboard did not load after login.").to_be_visible()
```

---

## `ui_testing.md` artifact

The skill's per-app artifact (parallels `e2e_testing.md` / `validation_findings.md`): append a dated
section to `.documentation/{app}/ui_testing.md` — per-app working notes live under
`.documentation/{app}/` (gitignored, never synced). Get the date with `date '+%Y-%m-%d'`. Create the
file if it doesn't exist; append a new `##` section if it does (never overwrite an earlier run).

**No sensitive data.** Never write credentials, passwords, tokens, or credential-file contents into
the artifact. Credential *key names* are fine; their *values* are not. **Do not include the base URL.**

````markdown
## {App} — UI regression test run ({YYYY-MM-DD})

### Scope
<one line — what was requested / scenarios covered>

### Discovered
- Login flow: <form fields, submit control, element that confirms success | none — public app>
- Page title(s): "<exact title used in to_have_title>"
- First-run configuration page: <yes — what it does / how it's confirmed | none>

### Created
- Page objects: `pages/{pkg}/{pkg}_login_page.py`, `pages/{pkg}/{pkg}_{feature}_page.py`
- Tests: `test_{pkg}_startup`, `test_{pkg}_login` (if the app has a login), `test_{pkg}_<scenario>`

### Verified
- Boxes deployed (ids only): exploration <id>; final green run on fresh deploy <id>

### Notes / issues
- <slow operations needing `timeout=...`, flaky areas, ambiguous selectors, anything a future run should know>
- Troubleshooting entries added this session: <list | none>
````

