EXPECTED_CLUSTER_SIZE = 3
EXPECTED_STANDBY_COUNT = 2
PROBE_VALUE = "regression_value"
READ_ONLY_ERROR = "read-only transaction"


def test_postgresql_service_active_and_answers_queries(postgresql_service):
    # Verifies that the server unit is running and actually answers SQL
    assert postgresql_service.is_active() == "active", "The PostgreSQL server unit is not active."
    assert postgresql_service.query("SELECT 1;") == "1", "PostgreSQL did not answer a trivial query."


def test_postgresql_cluster_has_one_primary_and_two_standbys(postgresql_service):
    # Verifies that repmgr sees a complete cluster with a single primary and every standby following it
    nodes = postgresql_service.cluster_nodes()

    assert len(nodes) == EXPECTED_CLUSTER_SIZE, (
        f"Expected {EXPECTED_CLUSTER_SIZE} nodes in the cluster, found: {nodes}"
    )
    for node in nodes:
        assert node["status"] == "running", f"Node {node['name']} is not running: {node['status']}"

    primaries = [node for node in nodes if node["role"] == "primary"]
    standbys = [node for node in nodes if node["role"] == "standby"]

    assert len(primaries) == 1, f"The cluster does not have exactly one primary: {primaries}"
    assert len(standbys) == EXPECTED_STANDBY_COUNT, (
        f"Expected {EXPECTED_STANDBY_COUNT} standbys, found: {standbys}"
    )
    for standby in standbys:
        assert standby["upstream"] == primaries[0]["name"], (
            f"{standby['name']} follows {standby['upstream']!r}, not the primary."
        )


def test_postgresql_write_replicates_to_every_standby(postgresql_service, unique_table):
    # Verifies replication end to end: a row written on the primary is read back from each standby
    _, stderr, exit_code = postgresql_service.create_probe_table(unique_table, PROBE_VALUE)
    assert exit_code == 0, f"Could not create the probe table on the primary: {stderr}"

    standbys = postgresql_service.standby_names()
    reads = {
        standby: (
            postgresql_service.read_probe_value_from(standby, unique_table),
            postgresql_service.is_in_recovery(standby),
        )
        for standby in standbys
    }

    postgresql_service.drop_probe_table(unique_table)

    assert len(standbys) == EXPECTED_STANDBY_COUNT, (
        f"Expected {EXPECTED_STANDBY_COUNT} standbys to read back from, found: {standbys}"
    )
    for standby, (value, in_recovery) in reads.items():
        assert value == PROBE_VALUE, f"{standby} did not return the replicated row: {value!r}"
        assert in_recovery == "t", f"{standby} is not in recovery - it is not a standby."


def test_postgresql_standbys_reject_writes(postgresql_service, unique_table):
    # Verifies that a standby refuses writes
    _, stderr, exit_code = postgresql_service.create_probe_table(unique_table, PROBE_VALUE)
    assert exit_code == 0, f"Could not create the probe table on the primary: {stderr}"

    standbys = postgresql_service.standby_names()
    attempts = {
        standby: postgresql_service.attempt_write_on(standby, unique_table)
        for standby in standbys
    }

    postgresql_service.drop_probe_table(unique_table)

    assert standbys, "No standby was found to test against."
    for standby, (stdout, stderr, exit_code) in attempts.items():
        assert exit_code != 0, f"{standby} accepted a write - it is not read-only."
        assert READ_ONLY_ERROR in stderr, (
            f"{standby} rejected the write for an unexpected reason: {stderr or stdout}"
        )
