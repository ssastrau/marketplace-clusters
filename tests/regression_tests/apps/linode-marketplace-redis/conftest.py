import uuid

import pytest

from regression_tests.services.redis.redis_service import RedisService
from regression_tests.utils.ssh import ssh_connection

CREDENTIALS_FILE = "/home/admin/.deployment-secrets.txt"
REDIS_PASSWORD_LABEL = "redis-cli --askpass"


@pytest.fixture(scope="session")
def credentials_file_path():
    """
    Returns the path to the credentials file on the Redis provisioner.

    Returns:
        str: Absolute path to the credentials file.
    """
    return CREDENTIALS_FILE


@pytest.fixture(scope="session")
def redis_password(ssh_credentials, credentials_file_path) -> str:
    """
    Extracts the Redis password from the credentials file.

    The file records it as a bare line underneath a label that ends in a colon with
    nothing after it, so the shared app_credentials fixture - which splits "Key: Value"
    within a single line - skips both lines and never sees the password. This reads the
    line following the label instead.

    Args:
        ssh_credentials: host, username, password.
        credentials_file_path: Absolute path to the credentials file on the VM.

    Returns:
        str: The Redis password.
    """
    host, username, password = ssh_credentials
    with ssh_connection(host, username, password) as client:
        _, stdout, _ = client.exec_command(f"cat {credentials_file_path}")
        lines = stdout.read().decode().splitlines()

    for index, line in enumerate(lines):
        if REDIS_PASSWORD_LABEL in line and index + 1 < len(lines):
            return lines[index + 1].strip()
    raise RuntimeError(f"No Redis password found under {REDIS_PASSWORD_LABEL!r} in {credentials_file_path}")


@pytest.fixture(scope="session")
def redis_service(remote_exec, redis_password):
    """
    Returns the service object the Redis tests drive the cluster through.

    Args:
        remote_exec: Callable running commands on the provisioner over SSH.
        redis_password: Password parsed out of the credentials file.

    Returns:
        RedisService: Service object exposing redis-cli actions over TLS.
    """
    return RedisService(remote_exec=remote_exec, password=redis_password)


@pytest.fixture
def unique_key() -> str:
    """
    Returns a key unique to this test, so a run leaves nothing behind that a later run
    could collide with.

    Returns:
        str: A fresh Redis key.
    """
    return f"regr:{uuid.uuid4().hex[:8]}"
