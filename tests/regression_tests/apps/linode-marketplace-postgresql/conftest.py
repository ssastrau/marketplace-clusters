import uuid

import pytest

from regression_tests.services.postgresql.postgresql_service import PostgresqlService


@pytest.fixture(scope="session")
def credentials_file_path():
    """
    Returns the path to the credentials file on the PostgreSQL provisioner. It holds the
    sudo account only - database access is peer-authenticated locally and trusted between
    cluster peers, so no test needs a password.

    Returns:
        str: Absolute path to the credentials file.
    """
    return "/home/admin/.deployment-secrets.txt"


@pytest.fixture(scope="session")
def postgresql_service(remote_exec):
    """
    Returns the service object the PostgreSQL tests drive the cluster through.

    Args:
        remote_exec: Callable running commands on the provisioner over SSH.

    Returns:
        PostgresqlService: Service object exposing psql and repmgr actions.
    """
    return PostgresqlService(remote_exec=remote_exec)


@pytest.fixture
def unique_table() -> str:
    """
    Returns a table name unique to this test, so a run leaves nothing behind that a later
    run could collide with.

    Returns:
        str: A fresh table name.
    """
    return f"regr_{uuid.uuid4().hex[:8]}"
