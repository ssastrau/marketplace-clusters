import json
import shlex

ELASTICSEARCH_HOST = "elasticsearch-1.local"
ELASTICSEARCH_PORT = 9200
KIBANA_CERT_DIR = "/etc/kibana/certs"


class ElkService:
    def __init__(self, http_session, remote_exec, base_url: str, elastic_username: str,
                 elastic_password: str):
        self.http_session = http_session
        self.remote_exec = remote_exec
        self.base_url = base_url
        self.elastic_username = elastic_username
        self.elastic_password = elastic_password

    def get_kibana_status(self) -> dict:
        response = self.http_session.get(
            f"{self.base_url}/api/status",
            auth=(self.elastic_username, self.elastic_password),
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def get_cluster_health(self) -> dict:
        auth = shlex.quote(f"elastic:{self.elastic_password}")
        command = (
            f"curl -s --cacert {KIBANA_CERT_DIR}/ca.crt "
            f"--cert {KIBANA_CERT_DIR}/kibana.local.crt "
            f"--key {KIBANA_CERT_DIR}/kibana.local.key "
            f"-u {auth} "
            f"https://{ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}/_cluster/health"
        )
        stdout, stderr, exit_code = self.remote_exec(command, timeout=60)
        if exit_code != 0:
            raise RuntimeError(
                f"Cluster health request failed (exit {exit_code}): {stderr or stdout}"
            )
        return json.loads(stdout)
