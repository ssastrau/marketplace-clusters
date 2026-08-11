import uuid

EXPECTED_CLUSTER_SIZE = 3
PROBE_VALUE = "regression_value"
EXPECTED_SSL_MODE = "660 mysql:mysql"


def test_galera_service_active_and_answers_queries(galera_service):
    # Verifies that the MariaDB unit is running and the node actually answers SQL,
    # which a systemd state alone does not prove.
    assert galera_service.is_active() == "active", "The MariaDB unit is not active."
    assert galera_service.query_scalar("SELECT 1;") == "1", "MariaDB did not answer a trivial query."


def test_galera_cluster_is_formed(galera_service):
    # Verifies that every node joined one primary component, which is what separates a
    # cluster from three isolated databases.
    status = galera_service.cluster_status()

    assert status.get("wsrep_cluster_size") == str(EXPECTED_CLUSTER_SIZE), (
        f"The cluster does not have {EXPECTED_CLUSTER_SIZE} members: {status}"
    )
    assert status.get("wsrep_cluster_status") == "Primary", (
        f"The cluster is not in a primary component - writes would be refused: {status}"
    )


def test_galera_node_is_synced(galera_service):
    # Verifies that this node finished state transfer and is serving replicated data
    # rather than still catching up.
    status = galera_service.cluster_status()

    assert status.get("wsrep_local_state_comment") == "Synced", (
        f"The node has not finished syncing with the cluster: {status}"
    )
    assert status.get("wsrep_ready") == "ON", f"The node is not ready to accept queries: {status}"
    assert status.get("wsrep_connected") == "ON", f"The node is not connected to the cluster: {status}"


def test_galera_write_is_certified_by_the_cluster(galera_service):
    # Verifies that a write is stored and replicated. With a 3-member primary component,
    # a commit only succeeds once the whole cluster certifies the write-set, and the
    # committed sequence number advancing is that replication showing up in the node's
    # own accounting.
    database = f"regr_{uuid.uuid4().hex[:8]}"

    before = galera_service.last_committed()

    _, stderr, exit_code = galera_service.create_probe_database(database, PROBE_VALUE)
    assert exit_code == 0, f"Could not create the probe database: {stderr}"

    stored = galera_service.read_probe_value(database)
    after = galera_service.last_committed()

    galera_service.drop_database(database)

    assert stored == PROBE_VALUE, f"The row did not come back from the database: {stored!r}"
    assert after > before, (
        f"The committed sequence number did not advance ({before} -> {after}) - "
        "the write was not replicated to the cluster."
    )


def test_galera_replication_traffic_is_encrypted(galera_service):
    # Verifies that the replication link runs over TLS and that the key material it uses
    # is not world-readable.
    options = galera_service.provider_options()

    assert options.get("socket.ssl") == "YES", (
        f"Galera replication is not using TLS: socket.ssl={options.get('socket.ssl')!r}"
    )
    assert options.get("gmcast.listen_addr", "").startswith("ssl://"), (
        f"The replication listener is not an ssl:// endpoint: {options.get('gmcast.listen_addr')!r}"
    )

    modes = galera_service.ssl_file_modes()

    assert len(modes) == 3, f"Some galera TLS files are missing: {modes}"
    for name, mode in modes.items():
        assert mode == EXPECTED_SSL_MODE, f"{name} has unexpected permissions: {mode}"


def test_galera_write_is_readable_from_every_other_node(galera_service):
    # Verifies replication end to end: a row written here is read back from each of the
    # other nodes over the private network, and each of them identifies itself, so the
    # value provably came from that node's copy and not from this one.
    database = f"regr_{uuid.uuid4().hex[:8]}"
    username = f"regr_{uuid.uuid4().hex[:8]}"
    password = uuid.uuid4().hex

    _, stderr, exit_code = galera_service.create_remote_user(username, password)
    assert exit_code == 0, f"Could not create the remote test user: {stderr}"

    _, stderr, exit_code = galera_service.create_probe_database(database, PROBE_VALUE)
    assert exit_code == 0, f"Could not create the probe database: {stderr}"

    peers = galera_service.peer_addresses()
    reads = {
        peer: (
            galera_service.read_probe_value_from(peer, database, username, password),
            galera_service.node_name_of(peer, username, password),
        )
        for peer in peers
    }

    galera_service.drop_database(database)
    galera_service.drop_remote_user(username)

    assert len(peers) == EXPECTED_CLUSTER_SIZE - 1, (
        f"Expected {EXPECTED_CLUSTER_SIZE - 1} peers to read back from, found: {peers}"
    )
    for peer, (value, node_name) in reads.items():
        assert value == PROBE_VALUE, f"{peer} did not return the replicated row: {value!r}"
        assert node_name and node_name != galera_service.local_node_name(), (
            f"The read from {peer} was answered by {node_name!r}, not a different node."
        )
