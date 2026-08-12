import re
import shlex

KAFKA_DIRECTORY = "/etc/kafka"
BIN_DIRECTORY = f"{KAFKA_DIRECTORY}/bin"
SSL_DIRECTORY = f"{KAFKA_DIRECTORY}/ssl"
TRUSTSTORE = f"{SSL_DIRECTORY}/truststore/server.truststore.jks"
CLIENT_PROPERTIES = "/root/regression-client.properties"

CLIENT_PROPERTIES_TEMPLATE = """security.protocol=SSL
ssl.truststore.location={truststore}
ssl.truststore.password={truststore_password}
ssl.keystore.location={keystore}
ssl.keystore.password={keystore_password}
ssl.key.password={keystore_password}
"""

BROKER_PATTERN = re.compile(r"^(?P<host>\S+):(?P<port>\d+)\s+\(id:\s*(?P<id>\d+)", re.MULTILINE)

PARTITION_PATTERN = re.compile(
    r"Partition:\s*(?P<partition>\d+)\s+Leader:\s*(?P<leader>\S+)\s+"
    r"Replicas:\s*(?P<replicas>[\d,]+)\s+Isr:\s*(?P<isr>[\d,]+)"
)


class KafkaService:
    """
    Client actions for a Kafka KRaft cluster, executed on the provisioner over SSH.

    The client listener requires mutual TLS, so every CLI call is passed a properties
    file this object writes from the deployment's own keystore and truststore.
    Commands and output parsing belong here; assertions belong in the test functions.
    """

    UNIT = "kafka"
    BOOTSTRAP = "kafka1:9092"

    def __init__(self, remote_exec, truststore_password: str, keystore_password: str):
        """
        Args:
            remote_exec: Callable running commands on the provisioner over SSH.
            truststore_password: Truststore password from the credentials file.
            keystore_password: Keystore password from the credentials file.
        """
        self._run = remote_exec
        self._truststore_password = truststore_password
        self._keystore_password = keystore_password
        self._client_properties_written = False

    def is_active(self) -> str:
        """
        Returns the systemd state of the Kafka unit.

        Returns:
            str: The `systemctl is-active` output, e.g. "active".
        """
        stdout, _, _ = self._run(f"systemctl is-active {self.UNIT}")
        return stdout

    def quorum_status(self) -> dict[str, str]:
        """
        Returns the KRaft controller quorum's status. This is the metadata layer that
        replaced ZooKeeper, so a cluster without a leader here cannot serve metadata even
        if every broker process is up.

        Returns:
            dict[str, str]: Field name -> value, e.g. "CurrentVoters" -> "[1,2,3]".
        """
        stdout, _, _ = self._kafka("kafka-metadata-quorum.sh", "describe --status", timeout=120)
        status = {}
        for line in stdout.splitlines():
            name, separator, value = line.partition(":")
            if separator:
                status[name.strip()] = value.strip()
        return status

    def brokers(self) -> dict[str, str]:
        """
        Returns the brokers currently registered with the cluster.

        Returns:
            dict[str, str]: "host:port" -> broker id.
        """
        stdout, _, _ = self._kafka("kafka-broker-api-versions.sh", "", timeout=120)
        return {
            f"{match.group('host')}:{match.group('port')}": match.group("id")
            for match in BROKER_PATTERN.finditer(stdout)
        }

    def create_topic(self, topic: str, partitions: int, replication_factor: int) -> tuple[str, str, int]:
        """
        Creates a topic.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._kafka(
            "kafka-topics.sh",
            f"--create --topic {shlex.quote(topic)} "
            f"--partitions {partitions} --replication-factor {replication_factor}",
            timeout=120,
        )

    def describe_topic(self, topic: str) -> list[dict[str, str]]:
        """
        Returns each partition's leader, replica set and in-sync replica set. A replica
        missing from the ISR means the partition is under-replicated even though the
        topic exists with the requested replication factor.

        Returns:
            list[dict[str, str]]: One entry per partition.
        """
        stdout, _, _ = self._kafka(
            "kafka-topics.sh", f"--describe --topic {shlex.quote(topic)}", timeout=120
        )
        return [match.groupdict() for match in PARTITION_PATTERN.finditer(stdout)]

    def delete_topic(self, topic: str) -> tuple[str, str, int]:
        """
        Removes a topic created by a test.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        return self._kafka(
            "kafka-topics.sh", f"--delete --topic {shlex.quote(topic)}", timeout=120
        )

    def produce(self, topic: str, message: str) -> tuple[str, str, int]:
        """
        Publishes a single message through the console producer.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        properties = self._ensure_client_properties()
        return self._run(
            f"echo {shlex.quote(message)} | {BIN_DIRECTORY}/kafka-console-producer.sh "
            f"--bootstrap-server {self.BOOTSTRAP} --producer.config {properties} "
            f"--topic {shlex.quote(topic)}",
            timeout=180,
        )

    def consume(self, topic: str, timeout_ms: int = 30000) -> str:
        """
        Reads the topic from the beginning and returns the first message. The consumer
        exits on its own once one message arrives or the timeout expires, so it never
        blocks the run.

        Returns:
            str: Raw consumer output, which contains the message.
        """
        properties = self._ensure_client_properties()
        stdout, _, _ = self._run(
            f"{BIN_DIRECTORY}/kafka-console-consumer.sh "
            f"--bootstrap-server {self.BOOTSTRAP} --consumer.config {properties} "
            f"--topic {shlex.quote(topic)} --from-beginning --max-messages 1 "
            f"--timeout-ms {timeout_ms}",
            timeout=240,
        )
        return stdout

    def _ensure_client_properties(self) -> str:
        """
        Writes the mutual-TLS client config once per session and returns its path.

        Returns:
            str: Path to the client properties file on the box.
        """
        if not self._client_properties_written:
            hostname, _, _ = self._run("hostname")
            contents = CLIENT_PROPERTIES_TEMPLATE.format(
                truststore=TRUSTSTORE,
                truststore_password=self._truststore_password,
                keystore=f"{SSL_DIRECTORY}/keystore/{hostname}.keystore.jks",
                keystore_password=self._keystore_password,
            )
            self._run(
                f"printf '%s' {shlex.quote(contents)} > {CLIENT_PROPERTIES} && "
                f"chmod 600 {CLIENT_PROPERTIES}"
            )
            self._client_properties_written = True
        return CLIENT_PROPERTIES

    def _kafka(self, tool: str, arguments: str, timeout: int = 120) -> tuple[str, str, int]:
        """
        Runs a Kafka CLI tool against the cluster with the mutual-TLS client config.

        Returns:
            tuple[str, str, int]: (stdout, stderr, exit_code).
        """
        properties = self._ensure_client_properties()
        command = (
            f"{BIN_DIRECTORY}/{tool} --bootstrap-server {self.BOOTSTRAP} "
            f"--command-config {properties} {arguments}"
        )
        return self._run(command, timeout=timeout)
