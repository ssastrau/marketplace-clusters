import pytest

from regression_tests.services.cassandra.cassandra_service import CassandraService


@pytest.fixture(scope="session")
def credentials_file_path():
    """
    Returns the path to the credentials file on the Cassandra provisioner.

    Returns:
        str: Absolute path to the credentials file.
    """
    return "/home/admin/.credentials"


@pytest.fixture(scope="session")
def cassandra_credentials(app_credentials) -> tuple[str, str]:
    """
    Returns the database superuser the deployment creates. Cassandra's built-in
    `cassandra` account is stripped of its privileges during provisioning, so this is
    the only account that can log in.

    Args:
        app_credentials: Parsed credentials file from the provisioner.

    Returns:
        tuple[str, str]: (username, password).
    """
    return (
        app_credentials["Cassandra database user"],
        app_credentials["Cassandra superuser password"],
    )


@pytest.fixture(scope="session")
def cassandra_service(remote_exec, cassandra_credentials):
    """
    Returns the service object the Cassandra tests drive the cluster through.

    Args:
        remote_exec: Callable running commands on the provisioner over SSH.
        cassandra_credentials: Superuser username and password.

    Returns:
        CassandraService: Service object exposing cqlsh and nodetool actions.
    """
    username, password = cassandra_credentials
    return CassandraService(
        remote_exec=remote_exec,
        username=username,
        password=password,
    )
