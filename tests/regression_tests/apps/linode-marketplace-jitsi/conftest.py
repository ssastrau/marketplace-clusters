import pytest

from regression_tests.services.jitsi.jitsi_service import JitsiService


@pytest.fixture(scope="session")
def credentials_file_path():
    """
    Returns the path to the credentials file on the remote Jitsi server.

    Returns:
        str: Absolute path to the credentials file.
    """
    return "/home/admin/.credentials"


@pytest.fixture(scope="session")
def base_url(ssh_credentials):
    """
    Constructs the base HTTPS URL for the Jitsi app.

    Args:
        ssh_credentials: host

    Returns:
        str: The base URL of the Jitsi app.
    """
    host = ssh_credentials[0]
    linode_host = host.replace(".", "-")
    return f"https://{linode_host}.ip.linodeusercontent.com"


@pytest.fixture(scope="session")
def jitsi_service(remote_exec):
    """
    Returns the Jitsi service object used by the cluster tests.

    Args:
        remote_exec: Callable running commands on the jitsi node over SSH.

    Returns:
        JitsiService: Service object exposing jicofo's view of the cluster.
    """
    return JitsiService(remote_exec=remote_exec)
