import shlex

REPMGR_CONFIG = "/etc/repmgrd/repmgr.conf"
REPMGR_DATABASE = "repmgr"
REPMGR_USER = "repmgr"

PRIMARY_ROLE = "primary"
STANDBY_ROLE = "standby"


class PostgresqlService:
    """
    Client actions for a PostgreSQL cluster managed by repmgr, executed on the provisioner
    over SSH.

    Queries run as the postgres system user, which pg_hba trusts via peer authentication;
    cross-node queries go through the repmgr database, the only one peers may reach.
    Commands and output parsing belong here; assertions belong in the test functions.
    """

    UNIT = "postgresql@16-main"

    def __init__(self, remote_exec):
        """
        Args:
            remote_exec: Callable running commands on the provisioner over SSH.
        """
        self._run = remote_exec

    def is_active(self) -> str:
        """
        Returns the systemd state of the PostgreSQL server unit.

        Returns:
            str: The `systemctl is-active` output, e.g. "active".
        """
        stdout, _, _ = self._run(f"systemctl is-active {self.UNIT}")
        return stdout

    def query(self, statement: str, database: str = "postgres") -> str:
        """
        Runs a query locally as the postgres user and returns its single value. -tA strips
        headers and alignment so the result parses without framing.

        Args:
            statement: SQL returning one column of one row.
            database: Database to connect to.

        Returns:
            str: The value, or "" when the query returned nothing.
        """
        stdout, _, _ = self._psql(f"-d {shlex.quote(database)} -tAc {shlex.quote(statement)}")
        return stdout

    def cluster_nodes(self) -> list[dict[str, str]]:
        """
        Returns the cluster as repmgr sees it. The primary's status carries a leading "*",
        which is stripped so callers compare on the state alone.

        Returns:
            list[dict[str, str]]: One entry per node with id, name, role, status, upstream.
        """
        stdout, _, _ = self._run(
            f"sudo -u postgres repmgr -f {REPMGR_CONFIG} cluster show", timeout=90
        )
        nodes = []
        for line in stdout.splitlines():
            cells = [cell.strip() for cell in line.split("|")]
            if len(cells) < 5 or not cells[0].isdigit():
                continue
            nodes.append({
                "id": cells[0],
                "name": cells[1],
                "role": cells[2],
                "status": cells[3].lstrip("*").strip(),
                "upstream": cells[4],
            })
        return nodes

    def primary_name(self) -> str:
        """
        Returns the name of the node currently acting as primary.

        Returns:
            str: The primary's node name, or "" when there is none.
        """
        for node in self.cluster_nodes():
            if node["role"] == PRIMARY_ROLE:
                return node["name"]
        return ""

    def standby_names(self) -> list[str]:
        """
        Returns the names of the standby nodes, which double as the hostnames peers are
        reachable on (the playbook writes them into /etc/hosts).

        Returns:
            list[str]: Standby node names.
        """
        return [node["name"] for node in self.cluster_nodes() if node["role"] == STANDBY_ROLE]

    def create_probe_table(self, table: str, value: str) -> tuple[str, str, int]:
        """
        Creates a table holding one row on the primary, in the repmgr database so that
        standbys can be queried for it without a password.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._psql(
            f"-d {REPMGR_DATABASE} -tAc "
            + shlex.quote(
                f"CREATE TABLE {table} (id int PRIMARY KEY, value text); "
                f"INSERT INTO {table} VALUES (1, '{value}');"
            )
        )

    def drop_probe_table(self, table: str) -> tuple[str, str, int]:
        """
        Removes a table created by a test.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._psql(f"-d {REPMGR_DATABASE} -tAc {shlex.quote(f'DROP TABLE IF EXISTS {table};')}")

    def read_probe_value_from(self, host: str, table: str) -> str:
        """
        Reads the probe row through another node over the private network, so the value
        comes from that node's own replica rather than this one's.

        Returns:
            str: The stored value, or "" when the row is missing or unreachable.
        """
        stdout, _, _ = self._psql(
            f"-h {shlex.quote(host)} -U {REPMGR_USER} -d {REPMGR_DATABASE} -tAc "
            + shlex.quote(f"SELECT value FROM {table} WHERE id = 1;"),
            timeout=90,
        )
        return stdout

    def is_in_recovery(self, host: str = "") -> str:
        """
        Returns whether a node is in recovery, which is how a standby identifies itself.

        Args:
            host: Peer to ask. Defaults to this node.

        Returns:
            str: "t" on a standby, "f" on the primary.
        """
        target = f"-h {shlex.quote(host)} -U {REPMGR_USER} -d {REPMGR_DATABASE}" if host else "-d postgres"
        stdout, _, _ = self._psql(
            f"{target} -tAc {shlex.quote('SELECT pg_is_in_recovery();')}", timeout=90
        )
        return stdout

    def attempt_write_on(self, host: str, table: str) -> tuple[str, str, int]:
        """
        Tries to insert through a peer. A standby must refuse this: accepting it would
        mean the node is writable and the cluster has two primaries.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._psql(
            f"-h {shlex.quote(host)} -U {REPMGR_USER} -d {REPMGR_DATABASE} -tAc "
            + shlex.quote(f"INSERT INTO {table} VALUES (2, 'should-not-be-written');"),
            timeout=90,
        )

    def _psql(self, arguments: str, timeout: int = 60) -> tuple[str, str, int]:
        """
        Runs psql as the postgres user. LC_ALL=C keeps locale warnings from perl-based
        helpers out of the output when the SSH client forwards a locale the box lacks.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._run(f"LC_ALL=C sudo -u postgres psql {arguments}", timeout=timeout)
