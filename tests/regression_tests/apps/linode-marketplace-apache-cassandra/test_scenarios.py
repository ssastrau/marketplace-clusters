import uuid

EXPECTED_CLUSTER_SIZE = 3
EXPECTED_VERSION_SERIES = "4.1."
PROBE_VALUE = "regression_value"
NODE_UP_AND_NORMAL = "UN"


def test_cassandra_service_active_and_answers_queries(cassandra_service):
    # Verifies that the Cassandra unit is running and the node actually serves CQL,
    # which a systemd state alone does not prove.
    assert cassandra_service.is_active() == "active", "The Cassandra unit is not active."

    stdout, stderr, exit_code = cassandra_service.query_release_version()

    assert exit_code == 0, f"cqlsh could not query the node: {stderr or stdout}"
    assert EXPECTED_VERSION_SERIES in stdout, (
        f"The node did not report a {EXPECTED_VERSION_SERIES}x release version: {stdout}"
    )


def test_cassandra_cluster_nodes_are_all_up(cassandra_service):
    # Verifies that every node joined and gossip sees them as up and normal, which is
    # what separates a cluster from three isolated databases.
    nodes = cassandra_service.cluster_nodes()

    assert len(nodes) == EXPECTED_CLUSTER_SIZE, (
        f"Expected {EXPECTED_CLUSTER_SIZE} nodes in nodetool status, found {len(nodes)}: {nodes}"
    )
    assert all(state == NODE_UP_AND_NORMAL for state, _ in nodes), (
        f"Not every Cassandra node is up and normal: {nodes}"
    )

    described = cassandra_service.describe_cluster()

    assert f"Live: {EXPECTED_CLUSTER_SIZE}" in described, (
        f"The cluster does not report {EXPECTED_CLUSTER_SIZE} live nodes: {described}"
    )
    assert "Unreachable: 0" in described, f"The cluster reports unreachable nodes: {described}"


def test_cassandra_credentials_file_superuser_can_log_in(cassandra_service, cassandra_credentials):
    # Verifies that the account written to the credentials file is the privileged one -
    # provisioning strips the built-in `cassandra` account, so this is the only way in.
    username, _ = cassandra_credentials

    roles = cassandra_service.roles()

    assert username in roles, f"{username} is not a role on the cluster: {roles}"
    is_superuser, can_login = roles[username]
    assert is_superuser, f"{username} is not a superuser: {roles}"
    assert can_login, f"{username} cannot log in: {roles}"


def test_cassandra_requires_client_certificate_over_tls(cassandra_service):
    # Verifies that the cluster enforces mutual TLS: an unencrypted client is refused,
    # and the client key pair the deployment generates is accepted.
    stdout, stderr, exit_code = cassandra_service.attempt_unencrypted_connection()

    assert exit_code != 0, "An unencrypted client connected - TLS is not being enforced."
    assert "Connection error" in stderr, (
        f"The unencrypted client failed for an unexpected reason: {stderr or stdout}"
    )

    stdout, stderr, exit_code = cassandra_service.query_release_version_with_client_certificate()

    assert exit_code == 0, f"The generated client certificate was rejected: {stderr or stdout}"
    assert EXPECTED_VERSION_SERIES in stdout, (
        f"The client-certificate connection did not return a version: {stdout}"
    )


def test_cassandra_replicates_writes_across_the_cluster(cassandra_service):
    # Verifies that a row written through one node is readable from the others, which is
    # the point of running a replicated cluster rather than a single database.
    keyspace = f"regression_{uuid.uuid4().hex[:8]}"

    _, stderr, exit_code = cassandra_service.create_replicated_keyspace(
        keyspace, EXPECTED_CLUSTER_SIZE
    )
    assert exit_code == 0, f"Could not create the replicated keyspace: {stderr}"

    _, stderr, exit_code = cassandra_service.insert_at_all_replicas(keyspace, 1, PROBE_VALUE)
    assert exit_code == 0, f"The write did not reach every replica: {stderr}"

    peers = cassandra_service.peer_addresses()
    reads = {peer: cassandra_service.read_from_node(keyspace, 1, peer) for peer in peers}

    cassandra_service.drop_keyspace(keyspace)

    assert len(peers) == EXPECTED_CLUSTER_SIZE - 1, (
        f"Expected {EXPECTED_CLUSTER_SIZE - 1} peers to read back from, found: {peers}"
    )
    for peer, output in reads.items():
        assert PROBE_VALUE in output, (
            f"{peer} did not return the replicated row: {output}"
        )
