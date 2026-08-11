import pytest

from regression_tests.services.galera.galera_service import GaleraService


@pytest.fixture(scope="session")
def galera_service(remote_exec):
    """
    Returns the service object the Galera tests drive the cluster through.

    The deployment writes no credentials file and leaves only unix_socket accounts, so
    there is no credentials_file_path fixture here and no base_url - the cluster has no
    HTTP surface and is reached as root on the box.

    Args:
        remote_exec: Callable running commands on the provisioner over SSH.

    Returns:
        GaleraService: Service object exposing mysql, ss and firewall-cmd actions.
    """
    return GaleraService(remote_exec=remote_exec)
