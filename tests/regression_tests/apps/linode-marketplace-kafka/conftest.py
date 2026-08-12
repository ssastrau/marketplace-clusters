import uuid

import pytest

from regression_tests.services.kafka.kafka_service import KafkaService


@pytest.fixture(scope="session")
def credentials_file_path():
    """
    Returns the path to the credentials file on the Kafka provisioner.

    Returns:
        str: Absolute path to the credentials file.
    """
    return "/home/admin/.credentials"


@pytest.fixture(scope="session")
def kafka_service(remote_exec, app_credentials):
    """
    Returns the service object the Kafka tests drive the cluster through.

    The client listener requires mutual TLS, so the service object needs the keystore and
    truststore passwords to build a client config; Kafka itself has no user account to log
    in with.

    Args:
        remote_exec: Callable running commands on the provisioner over SSH.
        app_credentials: Parsed credentials file from the provisioner.

    Returns:
        KafkaService: Service object exposing the Kafka CLI tools over SSL.
    """
    return KafkaService(
        remote_exec=remote_exec,
        truststore_password=app_credentials["truststore_password"],
        keystore_password=app_credentials["keystore_password"],
    )


@pytest.fixture
def unique_topic() -> str:
    """
    Returns a topic name unique to this test, so a run leaves nothing behind that a later
    run could collide with. Kafka warns that names mixing '.' and '_' can collide in
    metric names, so the generated name contains neither.

    Returns:
        str: A fresh topic name.
    """
    return f"regr{uuid.uuid4().hex[:8]}"
