import re
import shlex

SSL_DIRECTORY = "/etc/ssl/mysql"
SSL_FILES = ["galera-ca-crt.pem", "galera-server-crt.pem", "galera-server-key.pem"]

CLUSTER_STATUS_VARIABLES = [
    "wsrep_cluster_size",
    "wsrep_cluster_status",
    "wsrep_local_state_comment",
    "wsrep_ready",
    "wsrep_connected",
    "wsrep_cluster_state_uuid",
]

HOSTS_BLOCK_PATTERN = re.compile(
    r"# BEGIN GALERA HOSTS(?P<block>.*?)# END GALERA HOSTS", re.DOTALL
)
HOST_ENTRY_PATTERN = re.compile(r"^\s*(\d+\.\d+\.\d+\.\d+)\s+(\S+)", re.MULTILINE)


class GaleraService:
    """
    Client actions for a MariaDB Galera cluster, executed on the provisioner over SSH.

    Both accounts the deployment leaves behind authenticate via unix_socket and 3306 is
    bound to loopback, so every query runs on the box as root rather than over TCP.
    Queries and output parsing belong here; assertions belong in the test functions.
    """

    UNIT = "mariadb"

    def __init__(self, remote_exec):
        """
        Args:
            remote_exec: Callable running commands on the provisioner over SSH.
        """
        self._run = remote_exec

    def is_active(self) -> str:
        """
        Returns the systemd state of the MariaDB unit.

        Returns:
            str: The `systemctl is-active` output, e.g. "active".
        """
        stdout, _, _ = self._run(f"systemctl is-active {self.UNIT}")
        return stdout

    def query_scalar(self, statement: str) -> str:
        """
        Runs a statement and returns its single value, stripped of headers and framing.

        Args:
            statement: SQL returning one column of one row.

        Returns:
            str: The value, or "" when the query returned nothing.
        """
        stdout, _, _ = self._sql(statement)
        return stdout

    def cluster_status(self) -> dict[str, str]:
        """
        Returns the wsrep status variables that describe cluster membership and this
        node's place in it.

        Returns:
            dict[str, str]: Variable name -> value.
        """
        names = ", ".join(f"'{name}'" for name in CLUSTER_STATUS_VARIABLES)
        stdout, _, _ = self._sql(f"SHOW STATUS WHERE Variable_name IN ({names});")
        return self._parse_pairs(stdout)

    def last_committed(self) -> int:
        """
        Returns the sequence number of the last write-set the cluster committed. It
        advances on every replicated write, so a rising value shows the node is taking
        part in replication rather than writing locally.

        Returns:
            int: The wsrep_last_committed sequence number, or -1 if unavailable.
        """
        stdout, _, _ = self._sql("SHOW STATUS LIKE 'wsrep_last_committed';")
        pairs = self._parse_pairs(stdout)
        value = pairs.get("wsrep_last_committed", "")
        return int(value) if value.isdigit() else -1

    def provider_options(self) -> dict[str, str]:
        """
        Returns the galera provider options, which carry the replication link's TLS
        settings.

        Returns:
            dict[str, str]: Option name -> value, e.g. "socket.ssl" -> "YES".
        """
        stdout, _, _ = self._sql("SHOW VARIABLES LIKE 'wsrep_provider_options';")
        _, _, options = stdout.partition("\t")
        parsed = {}
        for option in options.split(";"):
            name, separator, value = option.partition("=")
            if separator:
                parsed[name.strip()] = value.strip()
        return parsed

    def create_probe_database(self, database: str, value: str) -> tuple[str, str, int]:
        """
        Creates a throwaway database holding one InnoDB row. InnoDB matters: galera only
        replicates transactional tables, so a MyISAM probe would never leave the node.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._sql(
            f"CREATE DATABASE {database}; "
            f"CREATE TABLE {database}.probe (id INT PRIMARY KEY, value VARCHAR(64)) ENGINE=InnoDB; "
            f"INSERT INTO {database}.probe VALUES (1, '{value}');"
        )

    def read_probe_value(self, database: str) -> str:
        """
        Reads the probe row back.

        Returns:
            str: The stored value, or "" when the row is missing.
        """
        return self.query_scalar(f"SELECT value FROM {database}.probe WHERE id = 1;")

    def drop_database(self, database: str) -> tuple[str, str, int]:
        """
        Removes a database created by a test.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._sql(f"DROP DATABASE IF EXISTS {database};")

    def peer_addresses(self) -> list[str]:
        """
        Returns the private addresses of the other cluster members, read from the
        /etc/hosts block the playbook writes - the only place on the box that names every
        node (wsrep_incoming_addresses reports "AUTO" and is no use here).

        Returns:
            list[str]: Cluster addresses excluding this node's own.
        """
        local, _, _ = self._run("hostname")
        stdout, _, _ = self._run("cat /etc/hosts")
        block = HOSTS_BLOCK_PATTERN.search(stdout)
        if not block:
            return []
        entries = HOST_ENTRY_PATTERN.findall(block.group("block"))
        return [address for address, hostname in entries if hostname != local]

    def local_node_name(self) -> str:
        """
        Returns this node's wsrep node name, for comparison against the name a peer
        reports.

        Returns:
            str: The wsrep_node_name of the node the tests connect to.
        """
        return self.query_scalar("SELECT @@wsrep_node_name;")

    def create_remote_user(self, username: str, password: str) -> tuple[str, str, int]:
        """
        Creates an account that can connect over TCP. The deployment leaves only
        unix_socket accounts, so a cross-node read has to bring its own credentials.
        Galera replicates account DDL in total order, so the user appears on every node.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._sql(
            f"CREATE USER '{username}'@'%' IDENTIFIED BY '{password}'; "
            f"GRANT ALL ON *.* TO '{username}'@'%';"
        )

    def drop_remote_user(self, username: str) -> tuple[str, str, int]:
        """
        Removes an account created by a test.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._sql(f"DROP USER IF EXISTS '{username}'@'%';")

    def read_probe_value_from(self, host: str, database: str, username: str,
                              password: str) -> str:
        """
        Reads the probe row through another node, over the private network, so the value
        comes from that node's own copy rather than this one's.

        Returns:
            str: The stored value, or "" when the row is missing or unreachable.
        """
        statement = f"SELECT value FROM {database}.probe WHERE id = 1;"
        stdout, _, _ = self._run(
            f"mysql -h {shlex.quote(host)} -u {shlex.quote(username)} "
            f"-p{shlex.quote(password)} -N -B -e {shlex.quote(statement)}",
            timeout=60,
        )
        return stdout

    def node_name_of(self, host: str, username: str, password: str) -> str:
        """
        Asks a node to identify itself, which is what proves a read was answered by a
        different member rather than looping back to this one.

        Returns:
            str: The remote node's wsrep node name, or "" when unreachable.
        """
        stdout, _, _ = self._run(
            f"mysql -h {shlex.quote(host)} -u {shlex.quote(username)} "
            f"-p{shlex.quote(password)} -N -B -e {shlex.quote('SELECT @@wsrep_node_name;')}",
            timeout=60,
        )
        return stdout

    def ssl_file_modes(self) -> dict[str, str]:
        """
        Returns the permissions and ownership of the TLS material the cluster replicates
        over.

        Returns:
            dict[str, str]: File name -> "mode owner:group", missing files omitted.
        """
        modes = {}
        for name in SSL_FILES:
            stdout, _, exit_code = self._run(
                f"stat -c '%a %U:%G' {SSL_DIRECTORY}/{name}"
            )
            if exit_code == 0:
                modes[name] = stdout
        return modes

    def _sql(self, statement: str) -> tuple[str, str, int]:
        """
        Runs SQL as root over the unix socket. -N drops column headers and -B switches to
        tab-separated output, so results parse without stripping the table framing.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._run(f"mysql -N -B -e {shlex.quote(statement)}", timeout=60)

    @staticmethod
    def _parse_pairs(stdout: str) -> dict[str, str]:
        """
        Parses tab-separated "name<TAB>value" lines into a dict.

        Returns:
            dict[str, str]: Parsed pairs.
        """
        pairs = {}
        for line in stdout.splitlines():
            name, separator, value = line.partition("\t")
            if separator:
                pairs[name.strip()] = value.strip()
        return pairs
