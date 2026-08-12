import re
import shlex

CA_CERTIFICATE = "/etc/redis/tls/ca.crt"
REDIS_PORT = 6379
SENTINEL_PORT = 26379
SENTINEL_MASTER_NAME = "mymaster"
INFO_FIELD_PATTERN = re.compile(r"^(?P<name>[a-z_0-9]+):(?P<value>.*)$", re.MULTILINE)
SLAVE_STATE_PATTERN = re.compile(r"^slave\d+:.*?state=(?P<state>\w+)", re.MULTILINE)


class RedisService:
    """
    Client actions for a Redis cluster with Sentinel, executed on the provisioner over SSH.

    The deployment disables the plaintext port entirely (`port 0`) and serves only on
    `tls-port`, so every call carries --tls and the CA certificate; the password comes from
    the credentials file. Commands and output parsing belong here; assertions belong in the
    test functions.
    """

    UNIT = "redis-server"
    SENTINEL_UNIT = "redis-sentinel"

    def __init__(self, remote_exec, password: str):
        """
        Args:
            remote_exec: Callable running commands on the provisioner over SSH.
            password: Redis password from the credentials file.
        """
        self._run = remote_exec
        self._password = password

    def is_active(self, unit: str = "") -> str:
        """
        Returns the systemd state of a Redis unit.

        Args:
            unit: Unit to check. Defaults to the server; pass SENTINEL_UNIT for Sentinel.

        Returns:
            str: The `systemctl is-active` output, e.g. "active".
        """
        stdout, _, _ = self._run(f"systemctl is-active {unit or self.UNIT}")
        return stdout

    def ping(self, host: str = "") -> str:
        """
        Sends PING over the TLS port.

        Args:
            host: Node to reach. Defaults to this one.

        Returns:
            str: "PONG" when the server answers.
        """
        return self._redis_cli("ping", host=host)

    def set_value(self, key: str, value: str, host: str = "") -> str:
        """
        Sets a key.

        Returns:
            str: "OK" on success, or the server's error text - redis-cli prints errors to
            stdout, so a rejection arrives here rather than as a failure.
        """
        return self._redis_cli(f"set {shlex.quote(key)} {shlex.quote(value)}", host=host)

    def get_value(self, key: str, host: str = "") -> str:
        """
        Reads a key back, optionally through another node.

        Returns:
            str: The stored value, or "" when the key is missing.
        """
        return self._redis_cli(f"get {shlex.quote(key)}", host=host)

    def delete_value(self, key: str, host: str = "") -> str:
        """
        Removes a key a test created.

        Returns:
            str: The number of keys removed.
        """
        return self._redis_cli(f"del {shlex.quote(key)}", host=host)

    def replication_info(self, host: str = "") -> dict[str, str]:
        """
        Returns the `INFO replication` fields for a node - its role, how many replicas are
        attached and, on a replica, the health of its link to the primary.

        Returns:
            dict[str, str]: Field name -> value.
        """
        output = self._redis_cli("info replication", host=host)
        return {
            match.group("name"): match.group("value").strip()
            for match in INFO_FIELD_PATTERN.finditer(output)
        }

    def replica_hosts(self) -> list[str]:
        """
        Returns the replicas' addresses as the primary reports them, so callers discover
        peers from the running cluster rather than hardcoding hostnames.

        Returns:
            list[str]: One address per replica, e.g. ["192.168.191.214", "192.168.155.226"].
        """
        return [
            value.split(",")[0].removeprefix("ip=")
            for name, value in self.replication_info().items()
            if name.startswith("slave") and name[5:].isdigit()
        ]

    def replica_states(self, host: str = "") -> list[str]:
        """
        Returns the connection state of each replica as the primary reports it. A replica
        counted in `connected_slaves` but not `online` is attached yet not caught up.

        Returns:
            list[str]: One state per replica, e.g. ["online", "online"].
        """
        output = self._redis_cli("info replication", host=host)
        return [match.group("state") for match in SLAVE_STATE_PATTERN.finditer(output)]

    def sentinel_quorum_check(self) -> str:
        """
        Asks Sentinel whether it can still reach a quorum and authorise a failover. A
        cluster that has lost quorum keeps serving reads and writes but can no longer
        promote a replica, so this is invisible from the data path.

        Returns:
            str: Raw `SENTINEL CKQUORUM` output.
        """
        return self._redis_cli(
            f"sentinel ckquorum {SENTINEL_MASTER_NAME}", port=SENTINEL_PORT, authenticate=False
        )

    def sentinel_master_name(self) -> str:
        """
        Returns the name of the master Sentinel is monitoring.

        Returns:
            str: The monitored master's name, or "" when none is configured.
        """
        output = self._redis_cli("sentinel masters", port=SENTINEL_PORT, authenticate=False)
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        return lines[lines.index("name") + 1] if "name" in lines else ""

    def _redis_cli(self, command: str, host: str = "", port: int = REDIS_PORT,
                   authenticate: bool = True) -> str:
        """
        Runs a redis-cli command over TLS. --no-auth-warning keeps the auth notice off
        stderr so it cannot muddy an assertion.

        Returns:
            str: The command's stdout.
        """
        invocation = f"redis-cli --tls --cacert {CA_CERTIFICATE} -p {port}"
        if host:
            invocation += f" -h {shlex.quote(host)}"
        if authenticate:
            invocation += f" -a {shlex.quote(self._password)} --no-auth-warning"
        stdout, _, _ = self._run(f"{invocation} {command}", timeout=60)
        return stdout
