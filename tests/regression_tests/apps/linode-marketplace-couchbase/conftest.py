import pytest


@pytest.fixture(scope="session")
def credentials_file_path():
    """
    Returns the path to the credentials file on the remote Couchbase server.

    Returns:
        str: Absolute path to the credentials file.
    """
    return "/home/admin/.credentials"


@pytest.fixture(scope="session")
def admin_credentials(app_credentials):
    """
    Returns the Couchbase Web Console admin login.
    The username is fixed by the playbook, so only the password comes from the
    credentials file on the remote server.

    Args:
        app_credentials: Parsed credentials file from the remote Couchbase server.

    Returns:
        tuple[str, str]: A (username, password) tuple.
    """
    return "Administrator", app_credentials["Couchbase Server Administrator Password"]


@pytest.fixture(scope="session")
def base_url(ssh_credentials):
    """
    Constructs the base HTTPS URL for the Couchbase app.

    Args:
        ssh_credentials: host

    Returns:
        str: The base URL of the Couchbase app.
    """
    host = ssh_credentials[0]
    linode_host = host.replace(".", "-")
    return f"https://{linode_host}.ip.linodeusercontent.com"
