# Troubleshooting

Recurring failure modes for Marketplace-app regression tests, with confirmed fixes. When a test
fails at Step 7, find the matching symptom here and apply the fix before guessing.

This file is **append-only knowledge**: add a new entry only when you hit a failure that isn't
already covered AND you've confirmed the fix (the test passed afterwards). See Step 8 in `SKILL.md`
for the capture rules. Keep the `Symptom → Cause → Fix` shape so entries stay scannable.

**Out of scope: deployment failures.** A failed StackScript deploy is a HARD STOP handed to the
operator (`SKILL.md` Step 3) — never something to troubleshoot here. This file covers the skill's
own steps: SSH reads, browser exploration, and the pytest run.

---

## SSL / certificate errors (`net::ERR_CERT_AUTHORITY_INVALID`, `SEC_ERROR_*`)

- **Symptom:** Navigation fails with a certificate / SSL error before the page loads — either
  `browser_navigate` during exploration (Step 5) or a test at runtime (Step 7).
- **Cause:** `*.ip.linodeusercontent.com` test deploys use self-signed certs.
  - *Exploration:* the Playwright MCP browser rejects them unless the MCP server was launched
    with `--ignore-https-errors` (the Step 1 setup command includes it).
  - *Tests:* the global `context` fixture already sets `ignore_https_errors=True` (`conftest.py`),
    so this only appears when the page was **not** created through the `context` fixture — e.g. a
    raw `browser.new_page()` or a second tab opened without inheriting the context options.
- **Fix:** Exploration → re-add the Playwright MCP with the flags and restart the chat:
  `claude mcp add playwright -- npx @playwright/mcp@latest --headless --ignore-https-errors`.
  Tests → use the `context` fixture as the page in every test; if you need a second tab, open it
  from the same context (`context.context.new_page()` / `BasePage.open_new_tab`) so it inherits
  `ignore_https_errors`.

---

## Every page returns `401 Unauthorized`

- **Symptom:** The app loads nothing; the browser shows a native Basic Auth prompt or all requests
  return 401.
- **Cause:** The app sits behind HTTP Basic Auth (e.g. htpasswd) and no credentials were supplied
  to the browser context. The global `http_credentials` fixture returns `None` by default.
- **Fix:** Override `http_credentials` in the app's `conftest.py` (see the "HTTP Basic Auth"
  template in `templates/test-file-templates.md`). The global `context` fixture forwards it to
  `new_context(http_credentials=...)` automatically — no test changes needed.

---

## First-run configuration page never appears

- **Symptom:** A test that expects the first-run setup/onboarding page lands on the normal
  dashboard instead, and its assertions fail.
- **Cause:** The first-run configuration page shows **once** per instance. A previous run already
  completed it on this VM, so it's gone for good.
- **Fix:** Redeploy a fresh box via the Linode MCP (the skill's Step 7b mechanics) and run the
  suite there — that's the only place first-run tests can pass. Expected when iterating on the
  exploration box (Step 7a): don't weaken the test to pass on a used VM, and never assume a rerun
  on the same box can go green if the suite includes first-run tests.

---

## Strict-mode locator violation on a "create content" scenario (duplicate items found)

- **Symptom:** A test that creates content (article, post, menu item, etc.) and then asserts it
  appears fails with a Playwright strict-mode violation — the locator resolves to 2+ elements with
  the same name/title, even though the test only created one.
- **Cause:** Exploration (Step 5) submitted the same create-content form to learn the resulting page
  shape, and/or the test was re-run against the same VM without redeploying. Each run adds another
  item with the same fixture title, so the box no longer matches the single-item state a genuinely
  fresh deploy would have.
- **Fix:** Don't paper over this with `.first` or similar — that masks a real regression if the app
  ever actually creates duplicates. On the **exploration box** (Step 7a) this is expected
  consumed-state, same as the first-run page above but for ordinary content: either delete the
  exploration-created items via the app's admin UI so you can keep iterating, or leave the
  scenario for the fresh box. The assertion is **proven on the fresh redeploy** (Step 7b), where
  exactly one matching item will exist and the test must pass as written.

---

## SSH host-key mismatch (Step 4 `ssh` read, or `SSHException` at test run)

- **Symptom:** Either the plain `ssh root@<ip>` reads (Step 4) fail with
  `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!`, or the pytest run (Step 7) raises
  `Host key verification failed for <host>. The server's host key does not match the expected key.`
- **Cause:** The VM at that IP was rebuilt/redeployed, so it presents a different host key. For the
  plain `ssh` reads the stale key lives in your `~/.ssh/known_hosts`; the suite's SSH helper
  instead pins the key on first contact (TOFU, `utils/ssh.py`) per-process.
- **Fix:** For the Step 4 reads, clear the stale entry with `ssh-keygen -R <ip>` and retry. For the
  pytest variant there is no stale `known_hosts` to clear (the key is pinned per-process) — just
  re-run against the current VM. If it persists on a stable VM, you're pointing at the wrong
  IP / `LINODE_IPV4`.

---

## `KeyError` on `app_credentials["..."]`

- **Symptom:** A test raises `KeyError` when reading a credential key.
- **Cause:** `app_credentials` parses the credentials file verbatim as `Key: Value` pairs
  (`utils/ssh.py`). The key string in the test doesn't match the file exactly (wrong casing, extra
  space, renamed field).
- **Fix:** Re-read the credentials file (Step 4b) and copy the key name exactly as printed, then
  use it verbatim in the test.

---

## `App URL` or `Credentials File` missing from `/etc/motd`

- **Symptom:** Step 4a returns `None` for `App URL` or `Credentials File` — the MOTD exists but
  doesn't contain one or both of those keys.
- **Cause:** Some apps (e.g. CyberPanel, which uses LiteSpeed's own setup scripts) write
  deployment information to the interactive shell welcome message instead of, or in addition to,
  `/etc/motd`. The standard MOTD parser never sees it.
- **Fix:** Open an interactive SSH shell session and capture the welcome output printed on first
  login — it typically contains the app URL, admin panel path, and instructions for retrieving
  credentials. Use that output to determine `base_url` and the credentials file path before
  proceeding with Step 4b.

---

## Playwright MCP snapshot renders `title` attributes as `aria-label` in YAML output

- **Symptom:** A locator like `[aria-label^="Some text"]` derived from the MCP snapshot yields
  `<element(s) not found>` at runtime even though the element is clearly visible on the page.
- **Cause:** The Playwright MCP `browser_snapshot` tool serialises HTML `title` attributes as
  `aria-label` in its YAML output (e.g. `generic "System uptime: …" [ref=eN]`). The real DOM
  element has no `aria-label` — only a `title` attribute (or neither). Copying the MCP-reported
  "aria-label" value directly into a CSS or Playwright locator therefore matches nothing.
- **Fix:** Before writing the locator, verify the actual attribute in the live DOM:
  ```js
  // Run via browser_evaluate to find the real element for a known text node:
  () => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const results = [];
    let node;
    while ((node = walker.nextNode())) {
      if (node.textContent.trim() === 'Target Text') {
        const el = node.parentElement;
        results.push({ tag: el.tagName, id: el.id, className: el.className,
                       title: el.title, ariaLabel: el.getAttribute('aria-label') });
      }
    }
    return results;
  }
  ```
  Use the real `id`, `name`, or stable class from that output instead of the MCP-reported
  `aria-label`. Prefer `#id` selectors when an `id` is present.

---

## SPA login form not found within the default assertion timeout

- **Symptom:** `test_{pkg}_startup` fails with `<element(s) not found>` on the username input locator
  even though the page title assertion (`to_have_title`) passes and the page URL is already at the
  login path (e.g. `/signin`). Error shows `timeout 5000ms`.
- **Cause:** Single-page applications (SPAs) route client-side — `page.goto("/signin")` resolves
  once the HTML shell loads, but the login form is rendered asynchronously by the JS framework
  (React, Vue, etc.). The default Playwright assertion timeout (5 s) expires before the form
  elements are injected into the DOM.
- **Fix:** Add `timeout=30000` to the `to_be_visible()` assertion on the login form element in
  `test_{pkg}_startup`. This gives the SPA up to 30 s to render the form, which is consistent with
  how the suite already handles other slow operations. Also ensure you navigate directly to the
  login path (e.g. `{base_url}/signin`) rather than the SPA root (`base_url`) — the root adds an
  extra client-side redirect that further delays rendering.

---

## `app_credentials` silently resolves to the wrong account (repeated key names in the file)

- **Symptom:** No error — the login test authenticates, but with the wrong service account, or a
  `KeyError` fix per the entry above doesn't actually pick the intended value even after copying
  the key name verbatim.
- **Cause:** `app_credentials` (`utils/ssh.py`) parses the credentials file into a flat `Key: Value`
  dict with no notion of sections. Some apps' credentials files repeat the same key name multiple
  times for different service accounts, each preceded only by a comment (e.g. Wazuh's file lists
  `indexer_username`/`indexer_password` six times — admin, kibanaserver, kibanaro, logstash,
  readall, snapshotrestore). The parser overwrites on each occurrence, so the fixture ends up
  holding only the *last* one in the file, not the one a human would read as "the login".
- **Fix:** Do not rely on `app_credentials` for that key. Add a dedicated session-scoped fixture in
  the app's own `conftest.py` (do **not** redefine `app_credentials` itself) that re-reads the file
  via `regression_tests.utils.ssh.ssh_connection` and extracts the specific pair with a targeted
  regex or line-context parse (e.g. anchor on the literal account name, `indexer_username:\s*'admin'`,
  then capture the following `indexer_password` line). Reference it in tests under its own name
  (e.g. `wazuh_dashboard_credentials`) rather than `app_credentials[...]`.
  (confirmed on wazuh, 2026-07)

---

## Post-login landmark absent on a genuinely fresh account (two different landing states)

- **Symptom:** The login test's post-login assertion (`to_be_visible()` on a dashboard element
  captured during exploration) fails with `<element(s) not found>` on a **different** fresh
  deploy than the one exploration was done on — even after bumping the timeout per the SPA
  entry above.
- **Cause:** Some apps render two different first-login landing states depending on whether the
  account already has content (a seeded default project/workspace/item) at the moment of login:
  a populated dashboard, or an empty "welcome / create your first X" onboarding screen. Which one
  renders can depend on a backend seed step racing the first login, so exploration and the later
  verification run can land on different states even though both are logging into a fresh
  instance for the first time. A locator scoped to the populated-dashboard variant (e.g. a
  "create new" button that only exists once at least one item exists) doesn't match on the empty
  variant.
- **Fix:** Don't assert on an element specific to either landing-state variant. Use a persistent
  UI landmark present in **both** states — typically something in the app's top nav/header (user
  menu button, logo, account avatar) rather than main-content elements. Verify this by loading
  the live app twice if possible, or by reasoning about what markup is shared vs. state-dependent
  in the snapshot.
  (confirmed on langflow, 2026-07)

