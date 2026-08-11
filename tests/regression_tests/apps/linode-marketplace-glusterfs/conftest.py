import pytest

from regression_tests.services.glusterfs.glusterfs_service import GlusterfsService


@pytest.fixture(scope="session")
def credentials_file_path():
    """
    Returns the path to the credentials file on the GlusterFS provisioner. It holds the
    sudo account only - GlusterFS itself has no password auth, peers and clients
    authenticate by certificate.

    Returns:
        str: Absolute path to the credentials file.
    """
    return "/home/admin/.credentials"


@pytest.fixture(scope="session")
def glusterfs_service(remote_exec):
    """
    Returns the service object the GlusterFS tests drive the cluster through.

    Args:
        remote_exec: Callable running commands on the provisioner over SSH.

    Returns:
        GlusterfsService: Service object exposing gluster CLI and mount actions.
    """
    return GlusterfsService(remote_exec=remote_exec)
