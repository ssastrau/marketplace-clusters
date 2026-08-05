# Troubleshooting

Recurring failure modes for **backend** (headless / API-only) Marketplace-app regression tests, with
fixes. When a probe or test fails at Steps 4–7, find the matching symptom here and apply the fix
before guessing.

This file is **append-only knowledge**: add a new entry only when you hit a failure that isn't
already covered AND you've confirmed the fix (the test passed afterwards). See Step 8 in `SKILL.md`
for the capture rules. Keep the `Symptom → Cause → Fix` shape so entries stay scannable.

**Out of scope: deployment failures.** A failed StackScript deploy is a HARD STOP handed to the
operator (`SKILL.md` Step 3) — never something to troubleshoot here. This file covers the skill's own
steps: SSH reads, live service probing, and the pytest run. Browser-specific issues belong to
`/ui-regression-tests`'s troubleshooting file, not this one.

---

## `systemctl is-active` returns `inactive`/`failed` but the app clearly works (wrong unit name)

- **Symptom:** `test_{pkg}_service_active` fails — `is-active` returns `inactive`, `failed`, or
  `Unit <name> could not be found`, even though the client commands and API all work.
- **Cause:** The unit name isn't `<app>`. Many services run under a different unit
  (`postgresql@16-main`, `redis-server`, `wg-quick@wg0`, `mariadb`, a compose-wrapper unit), or the
  app is a container managed by `docker`/`docker compose` rather than a systemd unit at all.
- **Fix:** Discover the real unit during Step 5 before writing the test:
  `systemctl list-units --type=service | grep -i <app>` (and `systemctl list-units 'wg-quick*'` for
  templated units). For a containerized app there may be no app-named unit — assert on
  `docker ps --filter name=<app> --format '{{.Status}}'` containing `Up` instead. Put the exact
  discovered name in `{App}Service.UNIT`.

---

## Port test fails — service binds `127.0.0.1` only (this is usually CORRECT)

- **Symptom:** `test_{pkg}_port_listening` fails because the port isn't reachable from the runner, or
  `ss` shows `127.0.0.1:<port>` where the test asserted `0.0.0.0:<port>` (or vice-versa).
- **Cause:** Headless datastores are frequently bound to loopback and/or firewalled on purpose — a
  `127.0.0.1`-only bind is the intended security posture, not a bug. The test was written asserting
  the wrong posture, or it tried to reach a loopback port from the test runner.
- **Fix:** Assert the posture you actually observed in Step 5. If the service is loopback-bound,
  assert `"127.0.0.1:<port>"` appears in `ss -tlnH` (run over `remote_exec`, on the box) and reach
  the service itself with its client **on the box**, never from the runner. Only assert a public
  bind when the firewall genuinely opens that port. When unsure whether a bind *should* be public,
  cross-check `architecture_decisions.md` / the app's firewall rules — don't "fix" the test by
  opening it up.

---

## Client command fails with `command not found`

- **Symptom:** A probe or test running the app's CLI (`redis-cli`, `psql`, `nats`, `wg`) fails with
  `command not found` / exit code 127.
- **Cause:** The client binary isn't on `PATH` for a non-interactive SSH session, or the app ships
  only a server with no client installed (common for minimal container-based installs), or the CLI
  lives at an absolute path the login shell would have on `PATH` but `ssh host 'cmd'` does not.
- **Fix:** In Step 5, find the real client: `which <cli>` / `command -v <cli>`, or
  `ls /usr/lib/postgresql/*/bin`, or check whether the client only exists inside the container
  (`docker exec <name> <cli> ...`). Use the working invocation verbatim in the service method. If no
  client exists on the box at all, use a protocol-level check the box *can* do (a `curl` to the API,
  a `nc`/`ss` port probe) rather than inventing a CLI that isn't there.

---

## Service is `active` but not yet ready (startup race)

- **Symptom:** `is-active` returns `active`, but the next check (a query, an API call, a socket
  connect) fails intermittently — passes on a re-run, fails on a fresh box.
- **Cause:** systemd reports the unit active as soon as the process starts, but the service needs a
  few more seconds to open its socket / finish recovery / load data (DB WAL replay, index load,
  broker cluster form). The test raced the readiness window.
- **Fix:** Don't add blind `sleep`s. Poll for readiness in the service method with a bounded retry on
  the service's own readiness signal — e.g. loop `pg_isready` / `redis-cli ping` / the API's
  `/ready` endpoint a handful of times with a short gap, up to a sensible cap, before returning. Give
  the `remote_exec` / `http_session` call a generous `timeout`. Assert only once the readiness signal
  is positive.

---

## API probe fails with a TLS / certificate error

- **Symptom:** An HTTP check via `http_session` or a `requests` call raises
  `SSLError` / `CERTIFICATE_VERIFY_FAILED`; or `curl` to the API returns a cert error.
- **Cause:** Test deploys sit on `*.ip.linodeusercontent.com` with self-signed certs. The
  `http_session` fixture sets `verify=False`, so this only appears when the request was **not** made
  through `http_session` (a raw `requests.get`, or a `curl` without `-k`).
- **Fix:** Reach public HTTPS endpoints through the `http_session` fixture (it carries
  `verify=False`). For `curl`-over-SSH checks use `curl -sk` (the `-k` skips verification). Never
  disable verification globally in a way that leaks outside the test context.

---

## SSH host-key mismatch (Step 4 `ssh` read, or `SSHException` at test run)

- **Symptom:** Either the plain `ssh root@<ip>` reads (Step 4) fail with
  `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!`, or the pytest run (Step 7) raises
  `Host key verification failed for <host>. The server's host key does not match the expected key.`
- **Cause:** The VM at that IP was rebuilt/redeployed, so it presents a different host key. For the
  plain `ssh` reads the stale key lives in your `~/.ssh/known_hosts`; the suite's SSH helper instead
  pins the key on first contact (TOFU, `utils/ssh.py`) per-process.
- **Fix:** For the Step 4 reads, clear the stale entry with `ssh-keygen -R <ip>` and retry. For the
  pytest variant there is no stale `known_hosts` to clear (the key is pinned per-process) — just
  re-run against the current VM. If it persists on a stable VM, you're pointing at the wrong
  IP / `LINODE_IPV4`.

---

## `KeyError` on `app_credentials["..."]`

- **Symptom:** A test raises `KeyError` when reading a credential key.
- **Cause:** `app_credentials` parses the credentials file verbatim as `Key: Value` (or `Key=Value`)
  pairs (`utils/ssh.py`). The key string in the test doesn't match the file exactly (wrong casing,
  extra space, renamed field), or the value is on a differently-delimited line the parser skips.
- **Fix:** Re-read the credentials file (Step 4b) and copy the key name exactly as printed, then use
  it verbatim. If the file uses a delimiter the parser doesn't split on, extract that value in a
  dedicated app-conftest fixture instead of relying on `app_credentials`.

---

## `app_credentials` returns the wrong value (repeated key names in the file)

- **Symptom:** No error — a test authenticates with the wrong account, or a `KeyError` fix doesn't
  pick the intended value even after copying the key name verbatim.
- **Cause:** `app_credentials` (`utils/ssh.py`) parses the file into a flat `Key: Value` dict with no
  notion of sections. Some apps repeat the same key name for several service accounts (each preceded
  only by a comment), so the parser keeps only the **last** occurrence — not the one a human reads as
  "the login."
- **Fix:** Don't rely on `app_credentials` for that key. Add a dedicated session-scoped fixture in the
  app's own `conftest.py` (do **not** redefine `app_credentials`) that re-reads the file via
  `regression_tests.utils.ssh.ssh_connection` and extracts the specific pair with a targeted regex
  anchored on the literal account name. See the "Repeated-key credentials" template in
  `templates/test-file-templates.md`.

---

## `App URL` or `Credentials File` missing from `/etc/motd`

- **Symptom:** Step 4a finds no `App URL` and/or no `Credentials File` key in the MOTD.
- **Cause:** Two distinct situations for a headless app:
  1. **No `App URL` is normal** for a pure SSH-only service (a firewalled DB with no HTTP surface) —
     there simply is no browsable/HTTP endpoint. This is not an error.
  2. Some vendor-installer apps write deploy info to the interactive shell welcome instead of
     `/etc/motd`, so even the credentials path is missing from the parsed MOTD.
- **Fix:** For (1), omit `base_url` from the app conftest and drive everything over SSH — that's the
  expected shape for a headless service. For (2), open an interactive SSH shell and capture the
  welcome output printed on first login to find the credentials path (and any endpoint), then
  proceed with Step 4b.

---

## Every backend test errors on SSH auth (`AuthenticationException`) — root login is disabled

- **Symptom:** Every test that uses `remote_exec` (i.e. nearly all of them) fails at connection time
  with `paramiko.AuthenticationException` / `Authentication failed`, even though the box is up and the
  root password is correct.
- **Cause:** Backend tests run SSH on *every* test, authenticating as `LINODE_ROOT_USER` (default
  `root`) with `LINODE_ROOT_PASS` over paramiko. If the app's `test-vars.sh` sets `DISABLE_ROOT`, the
  deploy turns off password root login, so paramiko can't authenticate as root. (The browser suite
  rarely trips this because it only SSHes once, for the credentials read.)
- **Fix:** Run pytest as the app user instead of root — set `LINODE_ROOT_USER=<app-user>` alongside
  `LINODE_IPV4` / `LINODE_ROOT_PASS` (the app user's password is in the credentials file). Confirm
  that user can run the probe commands; where a command needs elevation (`ss -tlnp` process column,
  reading root-owned config/keys), prefix it with `sudo` in the service method. If the app user has no
  password and only key auth, note it in the hard-stop report — the suite's SSH helper uses password
  auth, so key-only boxes need the operator to supply a usable credential.

---

## Public endpoint returns `000` (connection failed) when probed from the box

- **Symptom:** During exploration (Step 5), `curl` to the app's **public** URL
  (`https://<host>.ip.linodeusercontent.com/...`) run **on the box** returns HTTP code `000`
  (curl couldn't connect) — even though the service is healthy and the loopback probe succeeds.
- **Cause:** NAT hairpin. A box hitting its own public IP from inside often can't route back to
  itself (the cloud network doesn't hairpin the public address), so the connection fails outright.
  It is **not** a service or auth failure — the endpoint is fine from anywhere else.
- **Fix:** Probe genuinely public endpoints from the **runner** (external vantage), not on the box.
  In tests, that means the public API goes through the `http_session` fixture (which runs on the
  runner), while loopback/firewalled endpoints go through `remote_exec` (`curl` on the box). If you
  need to sanity-check a public endpoint during exploration, run the `curl` from your local machine,
  not over SSH. Seeing `000` on-box next to a `200` loopback is the signature of this, and it
  confirms (rather than contradicts) the vantage split. (confirmed on chroma, 2026-07)

---

## A CLI generator/scaffold hangs or `Aborted!`s under `remote_exec` (interactive prompts)

- **Symptom:** A CLI functional check (e.g. a project scaffolder) run over `remote_exec` returns a
  non-zero exit with `Aborted!` / `invalid input` / `EOF`, or appears to hang — even though the same
  command works when you type it in an interactive shell.
- **Cause:** The command is an interactive wizard. Over a non-interactive SSH exec there's no TTY and
  no stdin, so each prompt gets EOF; some prompts loop on bad input and then abort. (CrewAI's
  `crewai create crew <name>` prompts for tools, step-by-step planning, and per-agent role/goal.)
- **Fix:** Drive it non-interactively. Prefer the tool's own non-interactive flags over piping fake
  answers (piping `yes`/`N` "works" but produces garbage — e.g. an agent literally named "n"). For
  crewai: `crewai create crew <name> --classic --skip_provider </dev/null` runs clean and emits the
  classic Python/YAML project. Always redirect stdin from `/dev/null` so a stray prompt fails fast
  instead of hanging, and discover the right flags with `--help` during Step 5 before writing the
  test. (confirmed on crewai, 2026-07)

---

## `remote_exec` reports exit code 0 but stdout is empty for a command you expected output from

- **Symptom:** A service method returns `""` and the assertion fails, even though running the same
  command by hand shows output.
- **Cause:** The tool writes to **stderr**, not stdout (many CLIs print status/prompts to stderr), or
  the command needs a TTY it doesn't get over a non-interactive `exec_command`, or output goes to a
  pager that produces nothing without a TTY.
- **Fix:** In the service method, capture stderr too (`out, err, code = remote_exec(cmd)`) and assert
  on whichever stream actually carries the result. Add `--no-pager` / `2>&1` / the CLI's
  non-interactive flag as needed. Confirm the exact stream during Step 5 before writing the assertion
  — don't assume stdout.

## A stdin-fed query client returns empty output (missing trailing newline)

- **Symptom:** A DB/REPL client that reads its query from stdin (piped in) exits 0 but produces no
  rows — `printf '%s' "RETURN 1;" | mgconsole …` returns `""`, while `echo "RETURN 1;" | mgconsole …`
  by hand shows the table. The exact same command "works in the terminal" but not from the service
  method.
- **Cause:** The client reads a **line** from stdin and only executes on the line terminator; a query
  piped without a trailing `\n` (e.g. `printf '%s'`) hits EOF mid-line and nothing runs. `echo` masks
  this because it appends a newline; `printf '%s'` does not.
- **Fix:** Terminate the piped query with a newline — `printf '%s\n' <query>` (or `echo`) — in the
  service method. Applies to any stdin-driven client piped through `remote_exec` (`mgconsole`,
  `cypher-shell`, `psql`/`mysql` fed via a heredoc/pipe rather than `-c`/`-e`). (confirmed on
  memgraph, 2026-07)

---

## A multi-statement query returns the right value with command tags prepended

- **Symptom:** An assertion comparing stdout to an expected value fails with extra lines in front —
  `assert out == "x-axis"` fails on `'CREATE TABLE\nINSERT 0 3\nx-axis'`. The value is correct; it is
  simply not the whole of stdout.
- **Cause:** SQL clients print a **status tag per statement** on stdout. When several statements are
  passed in one invocation (`psql -c "CREATE …; INSERT …; SELECT …"`), the setup statements emit
  `CREATE TABLE` / `INSERT 0 3` before the query result, so stdout is the concatenation of all of
  them. Flags that strip formatting (`-tA`, `-N -B`) suppress headers and alignment but **not** the
  command tags.
- **Fix:** Don't batch setup and assertion in one call. Run the DDL/DML as its own `remote_exec` call
  and assert only on its exit code, then run the `SELECT` as a separate call whose stdout is nothing
  but the result. This is also what makes a failure legible — you learn whether the seed or the query
  broke. Parsing the last line instead works but silently hides a failed setup statement. (confirmed
  on pgvector, 2026-07)
