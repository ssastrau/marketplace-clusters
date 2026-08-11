import re
import shlex

VOLUME_NAME = "data-volume"
BRICK_DIRECTORY = "/data"
SSL_DIRECTORY = "/etc/ssl"
SECURE_ACCESS_FILE = "/var/lib/glusterd/secure-access"
SSL_FILES = ["glusterfs.pem", "glusterfs.key", "glusterfs.ca", "dhparams.pem"]
BRICK_ROW_PATTERN = re.compile(
    r"^Brick\s+(?P<brick>\S+)\s+\S+\s+\S+\s+(?P<online>\S+)\s+\S+", re.MULTILINE
)
SELF_HEAL_ROW_PATTERN = re.compile(
    r"^Self-heal Daemon on (?P<node>\S+)\s+\S+\s+\S+\s+(?P<online>\S+)\s+\S+", re.MULTILINE
)
HEAL_BLOCK_PATTERN = re.compile(
    r"^Brick (?P<brick>\S+)\s*\nStatus:\s*(?P<status>.+?)\s*\nNumber of entries:\s*(?P<entries>\d+)",
    re.MULTILINE,
)
PEER_STATE_PATTERN = re.compile(
    r"^Hostname:\s*(?P<hostname>\S+).*?^State:\s*(?P<state>.+?)$", re.MULTILINE | re.DOTALL
)


class GlusterfsService:
    """
    Client actions for a GlusterFS trusted storage pool, executed on the provisioner over
    SSH. The gluster CLI talks to the local glusterd, which reports cluster-wide state, so
    peer and heal information is available without reaching another node.

    Queries and output parsing belong here; assertions belong in the test functions.
    """

    UNIT = "glusterd"
    VOLUME = VOLUME_NAME

    def __init__(self, remote_exec):
        """
        Args:
            remote_exec: Callable running commands on the provisioner over SSH.
        """
        self._run = remote_exec

    def is_active(self) -> str:
        """
        Returns the systemd state of the glusterd unit.

        Returns:
            str: The `systemctl is-active` output, e.g. "active".
        """
        stdout, _, _ = self._run(f"systemctl is-active {self.UNIT}")
        return stdout

    def volume_info(self) -> tuple[str, str, int]:
        """
        Returns raw `gluster volume info` output for the deployment's volume. Answering at
        all means the CLI reached a live glusterd.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._gluster(f"volume info {self.VOLUME}")

    def volume_options(self) -> dict[str, str]:
        """
        Returns the volume's reconfigured options, e.g. "server.ssl" -> "on".

        Returns:
            dict[str, str]: Option name -> value.
        """
        stdout, _, _ = self.volume_info()
        options = {}
        for line in stdout.splitlines():
            name, separator, value = line.partition(": ")
            if separator and "." in name:
                options[name.strip()] = value.strip()
        return options

    def peer_states(self) -> dict[str, str]:
        """
        Returns each peer's connection state as glusterd sees it.

        Returns:
            dict[str, str]: hostname -> state, e.g. "Peer in Cluster (Connected)".
        """
        stdout, _, _ = self._gluster("peer status")
        states = {}
        for block in stdout.split("Hostname:")[1:]:
            hostname = block.split("\n", 1)[0].strip()
            match = re.search(r"^State:\s*(.+)$", block, re.MULTILINE)
            if match:
                states[hostname] = match.group(1).strip()
        return states

    def pool_states(self) -> dict[str, str]:
        """
        Returns the trusted storage pool as glusterd lists it, including this node
        (reported as "localhost").

        Returns:
            dict[str, str]: hostname -> state, e.g. "Connected".
        """
        stdout, _, _ = self._gluster("pool list")
        states = {}
        for line in stdout.splitlines()[1:]:
            fields = line.split()
            if len(fields) >= 3:
                states[fields[1]] = fields[2]
        return states

    def brick_states(self) -> dict[str, str]:
        """
        Returns each brick's Online column from `gluster volume status`. The TCP port is
        deliberately ignored - it is assigned dynamically per node and per deploy.

        Returns:
            dict[str, str]: brick -> "Y" or "N".
        """
        stdout, _, _ = self._gluster(f"volume status {self.VOLUME}", timeout=90)
        return {
            match.group("brick"): match.group("online")
            for match in BRICK_ROW_PATTERN.finditer(stdout)
        }

    def self_heal_daemon_states(self) -> dict[str, str]:
        """
        Returns the self-heal daemon's Online column per node, which is what repairs
        divergent replicas.

        Returns:
            dict[str, str]: node -> "Y" or "N".
        """
        stdout, _, _ = self._gluster(f"volume status {self.VOLUME}", timeout=90)
        return {
            match.group("node"): match.group("online")
            for match in SELF_HEAL_ROW_PATTERN.finditer(stdout)
        }

    def heal_state(self) -> dict[str, tuple[str, int]]:
        """
        Returns each brick's heal status and pending entry count. Reported cluster-wide by
        the local glusterd, so replica divergence is visible without reaching a peer.

        Returns:
            dict[str, tuple[str, int]]: brick -> (status, pending entries).
        """
        stdout, _, _ = self._gluster(f"volume heal {self.VOLUME} info", timeout=120)
        return {
            match.group("brick"): (match.group("status").strip(), int(match.group("entries")))
            for match in HEAL_BLOCK_PATTERN.finditer(stdout)
        }

    def mount_volume(self, mount_point: str) -> tuple[str, str, int]:
        """
        Mounts the volume through the native FUSE client on this node. The client uses the
        same /etc/ssl material as the servers, so a mount only succeeds when client TLS is
        working.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._run(
            f"mkdir -p {shlex.quote(mount_point)} && "
            f"mount -t glusterfs localhost:/{self.VOLUME} {shlex.quote(mount_point)}",
            timeout=120,
        )

    def unmount_volume(self, mount_point: str) -> tuple[str, str, int]:
        """
        Unmounts the volume and removes the mount point.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._run(
            f"umount {shlex.quote(mount_point)} && rmdir {shlex.quote(mount_point)}",
            timeout=60,
        )

    def write_file(self, mount_point: str, name: str, content: str) -> tuple[str, str, int]:
        """
        Writes a file through the mount, which is the path a real client takes.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._run(
            f"printf '%s' {shlex.quote(content)} > {shlex.quote(f'{mount_point}/{name}')}",
            timeout=60,
        )

    def read_file(self, mount_point: str, name: str) -> str:
        """
        Reads a file back through the mount.

        Returns:
            str: The file's contents, or "" when it is missing.
        """
        stdout, _, _ = self._run(f"cat {shlex.quote(f'{mount_point}/{name}')}", timeout=60)
        return stdout

    def read_from_local_brick(self, name: str) -> str:
        """
        Reads the same file straight off this node's brick, bypassing the mount. Proves
        the write reached the underlying storage rather than only the client cache.

        Returns:
            str: The file's contents on the brick, or "" when it is missing.
        """
        stdout, _, _ = self._run(f"cat {shlex.quote(f'{BRICK_DIRECTORY}/{name}')}", timeout=60)
        return stdout

    def remove_file(self, mount_point: str, name: str) -> tuple[str, str, int]:
        """
        Removes a file a test created.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._run(f"rm -f {shlex.quote(f'{mount_point}/{name}')}", timeout=60)

    def ssl_file_modes(self) -> dict[str, str]:
        """
        Returns the permissions of the TLS material in /etc/ssl. GlusterFS reads its
        certificate from this hardcoded location - material generated anywhere else is
        invisible to it and every peer connection fails.

        Returns:
            dict[str, str]: File name -> octal mode, missing files omitted.
        """
        modes = {}
        for name in SSL_FILES:
            stdout, _, exit_code = self._run(f"stat -c '%a' {SSL_DIRECTORY}/{name}")
            if exit_code == 0:
                modes[name] = stdout
        return modes

    def management_encryption_enabled(self) -> bool:
        """
        Returns whether the secure-access marker is present, which is what turns on TLS for
        the management path between peers.

        Returns:
            bool: True when the file exists.
        """
        _, _, exit_code = self._run(f"test -f {SECURE_ACCESS_FILE}")
        return exit_code == 0

    def _gluster(self, arguments: str, timeout: int = 60) -> tuple[str, str, int]:
        """
        Runs a gluster CLI command on the box.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._run(f"gluster {arguments}", timeout=timeout)
