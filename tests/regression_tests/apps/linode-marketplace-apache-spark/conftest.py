import pytest

from regression_tests.services.spark.spark_service import SparkService


@pytest.fixture(scope="session")
def credentials_file_path():
    """
    Returns the path to the credentials file on the remote Spark master.

    Returns:
        str: Absolute path to the credentials file.
    """
    return "/home/admin/.credentials"


@pytest.fixture(scope="session")
def base_url(ssh_credentials):
    """
    Constructs the base HTTPS URL for the Spark master UI.

    Args:
        ssh_credentials: host

    Returns:
        str: The base URL of the Spark master UI.
    """
    host = ssh_credentials[0]
    linode_host = host.replace(".", "-")
    return f"https://{linode_host}.ip.linodeusercontent.com"


@pytest.fixture(scope="session")
def spark_ui_credentials(app_credentials):
    """
    Returns the HTTP Basic Auth login that nginx enforces in front of the master UI.

    Args:
        app_credentials: Parsed credentials file from the remote Spark master.

    Returns:
        tuple[str, str]: A (username, password) tuple.
    """
    return app_credentials["spark user"], app_credentials["spark ui password"]


@pytest.fixture
def http_credentials(spark_ui_credentials):
    """
    Overrides the global fixture so the browser context authenticates automatically.
    The Spark master UI has no login form; nginx protects it with HTTP Basic Auth.

    Args:
        spark_ui_credentials: (username, password) for the master UI.

    Returns:
        dict: Basic Auth credentials for the browser context.
    """
    username, password = spark_ui_credentials
    return {"username": username, "password": password}


@pytest.fixture(scope="session")
def spark_service(remote_exec):
    """
    Returns the Spark service object used by the cluster tests.

    Args:
        remote_exec: Callable running commands on the Spark master over SSH.

    Returns:
        SparkService: Service object exposing the master's view of the cluster.
    """
    return SparkService(remote_exec=remote_exec)
