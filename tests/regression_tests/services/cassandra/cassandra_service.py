import re
import shlex

SSL_DIRECTORY = "/etc/cassandra/ssl"
CASSANDRA_YAML = "/etc/cassandra/cassandra.yaml"

CQLSHRC_TEMPLATE = """[connection]
ssl = true
factory = cqlshlib.ssl.ssl_transport_factory
[ssl]
certfile = {ssl_directory}/ca/ca.crt
userkey = {ssl_directory}/key/{client}.key
usercert = {ssl_directory}/cert/{client}.crt
validate = true
"""

RELEASE_VERSION_QUERY = "SELECT release_version FROM system.local;"
LIVENESS_QUERY = "SELECT now() FROM system.local;"
ROLES_QUERY = "SELECT role, is_superuser, can_login FROM system_auth.roles;"
NODE_ROW_PATTERN = re.compile(r"^(\S+)\s+(\d+\.\d+\.\d+\.\d+)", re.MULTILINE)
DATACENTER_PATTERN = re.compile(r"^Datacenter:\s*(\S+)", re.MULTILINE)
ROLE_FLAGS = {"True": True, "False": False}


class CassandraService:
    """
    Client actions for an Apache Cassandra cluster, executed on the provisioner over SSH.

    The cluster binds 9042 to the private network and ufw only admits the cluster's own
    private IPs, so every command runs on the box rather than from the test runner.
    Queries and output parsing belong here; assertions belong in the test functions.
    """

    UNIT = "cassandra"

    def __init__(self, remote_exec, username: str, password: str):
        """
        Args:
            remote_exec: Callable running commands on the provisioner over SSH.
            username: Cassandra superuser from the credentials file.
            password: Password for that superuser.
        """
        self._run = remote_exec
        self._username = username
        self._password = password

    def is_active(self) -> str:
        """
        Returns the systemd state of the Cassandra unit.

        Returns:
            str: The `systemctl is-active` output, e.g. "active".
        """
        stdout, _, _ = self._run(f"systemctl is-active {self.UNIT}")
        return stdout

    def local_address(self) -> str:
        """
        Returns the private address this node serves CQL on, read from its own config
        rather than assumed, so the tests follow whatever the deployment assigned.

        Returns:
            str: The `listen_address` value from cassandra.yaml.
        """
        stdout, _, _ = self._run(
            f"grep '^listen_address:' {CASSANDRA_YAML} | awk '{{print $2}}'"
        )
        return stdout

    def datacenter(self) -> str:
        """
        Returns the datacenter name gossip reports, which the deployment sets to the
        Linode region.

        Returns:
            str: The datacenter name from `nodetool status`, or "" if absent.
        """
        match = DATACENTER_PATTERN.search(self.node_status())
        return match.group(1) if match else ""

    def node_status(self) -> str:
        """
        Returns raw `nodetool status` output.

        Returns:
            str: The command's stdout.
        """
        stdout, _, _ = self._run("nodetool status", timeout=60)
        return stdout

    def describe_cluster(self) -> str:
        """
        Returns raw `nodetool describecluster` output, which carries the live/unreachable
        counts and the schema version each node agrees on.

        Returns:
            str: The command's stdout.
        """
        stdout, _, _ = self._run("nodetool describecluster", timeout=60)
        return stdout

    def cluster_nodes(self) -> list[tuple[str, str]]:
        """
        Parses `nodetool status` into the cluster's membership view.

        Returns:
            list[tuple[str, str]]: (state, address) pairs, e.g. ("UN", "192.168.154.28").
        """
        return [
            (match.group(1), match.group(2))
            for match in NODE_ROW_PATTERN.finditer(self.node_status())
        ]

    def peer_addresses(self) -> list[str]:
        """
        Returns the other nodes' addresses, used to prove a write is readable from a
        coordinator that did not accept it.

        Returns:
            list[str]: Cluster addresses excluding this node's own.
        """
        local = self.local_address()
        return [address for _, address in self.cluster_nodes() if address != local]

    def query_release_version(self) -> tuple[str, str, int]:
        """
        Asks the node for its release version, which only answers once Cassandra is
        genuinely serving CQL rather than merely started.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._cql(RELEASE_VERSION_QUERY)

    def query_release_version_with_client_certificate(self, client: str = "client1") -> tuple[str, str, int]:
        """
        Runs the same query through the client key pair the deployment generates, which
        is the connection path the Marketplace guide documents for a client node.

        Args:
            client: Which generated client identity to use, e.g. "client1".

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._cql(RELEASE_VERSION_QUERY, home=self._write_client_certificate_profile(client))

    def attempt_unencrypted_connection(self) -> tuple[str, str, int]:
        """
        Tries to connect with no TLS settings whatsoever. The deployment writes a cqlshrc
        for root that turns TLS on, so this runs under a HOME holding no cqlshrc at all -
        otherwise the client would quietly negotiate TLS and the attempt would prove
        nothing about what the server enforces.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._cql(LIVENESS_QUERY, home=self._write_bare_profile(), use_ssl=False)

    def roles(self) -> dict[str, tuple[bool, bool]]:
        """
        Returns the cluster's roles with their privileges, parsed from the cqlsh table.

        Returns:
            dict[str, tuple[bool, bool]]: role name -> (is_superuser, can_login).
        """
        stdout, _, _ = self._cql(ROLES_QUERY)
        parsed = {}
        for line in stdout.splitlines():
            cells = [cell.strip() for cell in line.split("|")]
            # Skips the header, the dashed separator and the "(2 rows)" footer, none of
            # which carry a boolean in the flag columns.
            if len(cells) != 3 or cells[1] not in ROLE_FLAGS or cells[2] not in ROLE_FLAGS:
                continue
            parsed[cells[0]] = (ROLE_FLAGS[cells[1]], ROLE_FLAGS[cells[2]])
        return parsed

    def create_replicated_keyspace(self, keyspace: str, replication_factor: int) -> tuple[str, str, int]:
        """
        Creates a keyspace replicated across the cluster's datacenter, plus a table to
        write into.

        Args:
            keyspace: Keyspace name.
            replication_factor: Copies of each row to keep.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        statement = (
            f"CREATE KEYSPACE {keyspace} WITH replication = "
            f"{{'class':'NetworkTopologyStrategy','{self.datacenter()}':{replication_factor}}}; "
            f"CREATE TABLE {keyspace}.probe (id int PRIMARY KEY, value text);"
        )
        return self._cql(statement)

    def insert_at_all_replicas(self, keyspace: str, identifier: int, value: str) -> tuple[str, str, int]:
        """
        Writes a row at CONSISTENCY ALL, so the statement only succeeds once every
        replica has acknowledged it.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        statement = (
            f"CONSISTENCY ALL; "
            f"INSERT INTO {keyspace}.probe (id, value) VALUES ({identifier}, '{value}');"
        )
        return self._cql(statement)

    def read_from_node(self, keyspace: str, identifier: int, host: str) -> str:
        """
        Reads a row back through a specific coordinator at CONSISTENCY ONE, which makes
        the node answer from its own replica rather than fetching from the writer.

        Returns:
            str: Raw cqlsh output containing the selected value.
        """
        statement = (
            f"CONSISTENCY ONE; "
            f"SELECT value FROM {keyspace}.probe WHERE id = {identifier};"
        )
        stdout, _, _ = self._cql(statement, host=host)
        return stdout

    def drop_keyspace(self, keyspace: str) -> tuple[str, str, int]:
        """
        Removes a keyspace created by a test.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._cql(f"DROP KEYSPACE IF EXISTS {keyspace};")

    def _cql(self, statement: str, host: str = "", home: str = "", use_ssl: bool = True,
             timeout: int = 90) -> tuple[str, str, int]:
        """
        Runs a CQL statement through cqlsh on the box.

        Args:
            statement: The CQL to execute.
            host: Node to connect to. Defaults to this node's private address.
            home: HOME to run under, which selects the ~/.cassandra/cqlshrc profile.
                Defaults to root's, which the deployment configures for TLS.
            use_ssl: Whether to pass --ssl.
            timeout: Command timeout in seconds.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        target = host or self.local_address()
        command = ""
        if home:
            command += f"HOME={shlex.quote(home)} "
        command += (
            f"cqlsh {shlex.quote(target)} "
            f"-u {shlex.quote(self._username)} -p {shlex.quote(self._password)}"
        )
        if use_ssl:
            command += " --ssl"
        command += f" -e {shlex.quote(statement)}"
        return self._run(command, timeout=timeout)

    def _write_client_certificate_profile(self, client: str) -> str:
        """
        Writes the cqlshrc the Marketplace documentation tells an operator to build on a
        client node, using the client key pair the deployment generated.

        Returns:
            str: A HOME directory to run cqlsh under.
        """
        home = f"/tmp/regression-cqlsh-{client}"
        cqlshrc = CQLSHRC_TEMPLATE.format(ssl_directory=SSL_DIRECTORY, client=client)
        self._run(
            f"mkdir -p {home}/.cassandra && "
            f"printf '%s' {shlex.quote(cqlshrc)} > {home}/.cassandra/cqlshrc"
        )
        return home

    def _write_bare_profile(self) -> str:
        """
        Creates a HOME with no cqlshrc, so a connection attempt carries no TLS settings.

        Returns:
            str: A HOME directory to run cqlsh under.
        """
        home = "/tmp/regression-cqlsh-bare"
        self._run(f"rm -rf {home} && mkdir -p {home}")
        return home
