import uuid

EXPECTED_CLUSTER_SIZE = 3
EXPECTED_PEER_STATE = "Peer in Cluster (Connected)"
EXPECTED_VOLUME_LAYOUT = "1 x 3 = 3"
PROBE_VALUE = "regression_value"
EXPECTED_KEY_MODE = "600"


def test_glusterfs_service_active_and_cli_answers(glusterfs_service):
    # Verifies that glusterd is running and answers for its volume
    assert glusterfs_service.is_active() == "active", "The glusterd unit is not active."

    stdout, stderr, exit_code = glusterfs_service.volume_info()

    assert exit_code == 0, f"gluster volume info failed: {stderr or stdout}"
    assert "Status: Started" in stdout, f"The volume is not started: {stdout}"


def test_glusterfs_all_peers_are_connected(glusterfs_service):
    # Verifies that the trusted storage pool formed and every member is reachable
    peers = glusterfs_service.peer_states()

    assert len(peers) == EXPECTED_CLUSTER_SIZE - 1, (
        f"Expected {EXPECTED_CLUSTER_SIZE - 1} peers, found: {peers}"
    )
    for hostname, state in peers.items():
        assert state == EXPECTED_PEER_STATE, f"{hostname} is not connected: {state}"

    pool = glusterfs_service.pool_states()

    assert len(pool) == EXPECTED_CLUSTER_SIZE, (
        f"Expected {EXPECTED_CLUSTER_SIZE} nodes in the pool, found: {pool}"
    )
    for hostname, state in pool.items():
        assert state == "Connected", f"{hostname} is not connected to the pool: {state}"


def test_glusterfs_volume_is_replicated_with_all_bricks_online(glusterfs_service):
    # Verifies that the volume is a 3-way replica and that every brick and self-heal
    # daemon is actually serving
    stdout, _, _ = glusterfs_service.volume_info()

    assert "Type: Replicate" in stdout, f"The volume is not replicated: {stdout}"
    assert EXPECTED_VOLUME_LAYOUT in stdout, (
        f"The volume is not laid out as {EXPECTED_VOLUME_LAYOUT}: {stdout}"
    )

    bricks = glusterfs_service.brick_states()

    assert len(bricks) == EXPECTED_CLUSTER_SIZE, (
        f"Expected {EXPECTED_CLUSTER_SIZE} bricks, found: {bricks}"
    )
    for brick, online in bricks.items():
        assert online == "Y", f"Brick {brick} is not online: {online}"

    daemons = glusterfs_service.self_heal_daemon_states()

    assert len(daemons) == EXPECTED_CLUSTER_SIZE, (
        f"Expected {EXPECTED_CLUSTER_SIZE} self-heal daemons, found: {daemons}"
    )
    for node, online in daemons.items():
        assert online == "Y", f"The self-heal daemon on {node} is not running: {online}"


def test_glusterfs_write_and_read_through_a_mount(glusterfs_service):
    # Verifies the path a real client takes: mount the volume, write a file, read it back
    mount_point = f"/mnt/regr_{uuid.uuid4().hex[:8]}"
    name = f"probe_{uuid.uuid4().hex[:8]}.txt"

    _, stderr, exit_code = glusterfs_service.mount_volume(mount_point)
    assert exit_code == 0, f"Could not mount the volume: {stderr}"

    _, stderr, exit_code = glusterfs_service.write_file(mount_point, name, PROBE_VALUE)
    assert exit_code == 0, f"Could not write through the mount: {stderr}"

    through_mount = glusterfs_service.read_file(mount_point, name)
    on_brick = glusterfs_service.read_from_local_brick(name)

    glusterfs_service.remove_file(mount_point, name)
    glusterfs_service.unmount_volume(mount_point)

    assert through_mount == PROBE_VALUE, f"The mount did not return the file: {through_mount!r}"
    assert on_brick == PROBE_VALUE, f"The write did not reach the brick: {on_brick!r}"


def test_glusterfs_replicas_are_in_sync(glusterfs_service):
    # Verifies that every replica is connected
    heal = glusterfs_service.heal_state()

    assert len(heal) == EXPECTED_CLUSTER_SIZE, (
        f"Expected heal information for {EXPECTED_CLUSTER_SIZE} bricks, found: {heal}"
    )
    for brick, (status, entries) in heal.items():
        assert status == "Connected", f"Brick {brick} is not connected for healing: {status}"
        assert entries == 0, f"Brick {brick} has {entries} entries pending heal."


def test_glusterfs_tls_is_enabled_with_usable_certificates(glusterfs_service):
    # Verifies that transport encryption is on AND that the certificates sit where gluster
    # reads them from.
    options = glusterfs_service.volume_options()

    assert options.get("server.ssl") == "on", f"Server-side TLS is off: {options}"
    assert options.get("client.ssl") == "on", f"Client-side TLS is off: {options}"
    assert options.get("auth.ssl-allow"), f"No certificate allow-list is set: {options}"

    assert glusterfs_service.management_encryption_enabled(), (
        "The secure-access marker is missing - the management path is unencrypted."
    )

    modes = glusterfs_service.ssl_file_modes()

    assert len(modes) == 4, f"Some TLS files are missing from /etc/ssl: {modes}"
    assert modes.get("glusterfs.key") == EXPECTED_KEY_MODE, (
        f"The private key is not {EXPECTED_KEY_MODE}: {modes}"
    )
