import pytest

from regression_tests.services.elk.elk_service import ElkService


@pytest.fixture(scope="session")
def credentials_file_path():
    """
    Returns the path to the credentials file on the remote ELK server.

    Returns:
        str: Absolute path to the credentials file.
    """
    return "/home/admin/.credentials"


@pytest.fixture(scope="session")
def base_url(ssh_credentials):
    """
    Constructs the base HTTPS URL for Kibana.

    Args:
        ssh_credentials: host

    Returns:
        str: The base URL of the Kibana app.
    """
    host = ssh_credentials[0]
    linode_host = host.replace(".", "-")
    return f"https://{linode_host}.ip.linodeusercontent.com"


@pytest.fixture(scope="session")
def elastic_credentials(app_credentials):
    """
    Returns the Kibana login for the built-in superuser.
    The username is fixed by Elasticsearch, so only the password comes from the
    credentials file on the remote server.

    Args:
        app_credentials: Parsed credentials file from the remote ELK server.

    Returns:
        tuple[str, str]: A (username, password) tuple.
    """
    return "elastic", app_credentials["Elastic password"]


@pytest.fixture(scope="session")
def elk_service(http_session, remote_exec, base_url, elastic_credentials):
    """
    Returns the ELK service object used by the non-browser tests.

    Args:
        http_session: Shared requests.Session (self-signed certs allowed).
        remote_exec: Callable running commands on the Kibana node over SSH.
        base_url: The base URL of the Kibana app.
        elastic_credentials: (username, password) for the elastic superuser.

    Returns:
        ElkService: Service object exposing Kibana status and cluster health.
    """
    username, password = elastic_credentials
    return ElkService(
        http_session=http_session,
        remote_exec=remote_exec,
        base_url=base_url,
        elastic_username=username,
        elastic_password=password,
    )
