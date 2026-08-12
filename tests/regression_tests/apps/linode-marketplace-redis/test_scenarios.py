from regression_tests.services.redis.redis_service import RedisService

EXPECTED_REPLICA_COUNT = 2
EXPECTED_SENTINEL_COUNT = 3
SENTINEL_MASTER_NAME = "mymaster"
PROBE_VALUE = "regression_value"
READONLY_ERROR = "READONLY"


def test_redis_service_active_and_answers_ping(redis_service):
    # Verifies that the Redis unit is running and answers
    assert redis_service.is_active() == "active", "The Redis unit is not active."
    assert redis_service.ping() == "PONG", "Redis did not answer PING over TLS."


def test_redis_sentinel_can_reach_quorum(redis_service):
    # Verifies that Sentinel is monitoring the primary and can still authorise a failover
    assert redis_service.is_active(RedisService.SENTINEL_UNIT) == "active", (
        "The Redis Sentinel unit is not active."
    )
    assert redis_service.sentinel_master_name() == SENTINEL_MASTER_NAME, (
        f"Sentinel is not monitoring {SENTINEL_MASTER_NAME}."
    )

    quorum = redis_service.sentinel_quorum_check()

    assert "OK" in quorum, f"Sentinel cannot reach a quorum: {quorum}"
    assert f"{EXPECTED_SENTINEL_COUNT} usable Sentinels" in quorum, (
        f"Expected {EXPECTED_SENTINEL_COUNT} usable sentinels: {quorum}"
    )


def test_redis_primary_has_every_replica_online(redis_service):
    # Verifies that both replicas are attached and caught up
    info = redis_service.replication_info()

    assert info.get("role") == "master", f"This node is not the primary: {info.get('role')!r}"
    assert info.get("connected_slaves") == str(EXPECTED_REPLICA_COUNT), (
        f"Expected {EXPECTED_REPLICA_COUNT} replicas, got {info.get('connected_slaves')!r}"
    )

    states = redis_service.replica_states()

    assert states == ["online"] * EXPECTED_REPLICA_COUNT, f"Not every replica is online: {states}"

    for host in redis_service.replica_hosts():
        replica = redis_service.replication_info(host=host)
        assert replica.get("role") == "slave", f"{host} does not report itself as a replica."
        assert replica.get("master_link_status") == "up", (
            f"{host} has lost its link to the primary: {replica.get('master_link_status')!r}"
        )


def test_redis_write_replicates_to_every_replica(redis_service, unique_key):
    # Verifies replication end to end: a key written on the primary is read back from each replica
    assert redis_service.set_value(unique_key, PROBE_VALUE) == "OK", (
        "The primary did not accept the write."
    )

    hosts = redis_service.replica_hosts()
    reads = {host: redis_service.get_value(unique_key, host=host) for host in hosts}

    redis_service.delete_value(unique_key)

    assert len(hosts) == EXPECTED_REPLICA_COUNT, (
        f"Expected {EXPECTED_REPLICA_COUNT} replicas to read back from, found: {hosts}"
    )
    for host, value in reads.items():
        assert value == PROBE_VALUE, f"{host} did not return the replicated value: {value!r}"


def test_redis_replicas_reject_writes(redis_service, unique_key):
    # Verifies that a replica refuses writes
    hosts = redis_service.replica_hosts()
    rejections = {host: redis_service.set_value(unique_key, "should-not-be-written", host=host)
                  for host in hosts}

    assert len(hosts) == EXPECTED_REPLICA_COUNT, (
        f"Expected {EXPECTED_REPLICA_COUNT} replicas to test against, found: {hosts}"
    )
    for host, response in rejections.items():
        assert READONLY_ERROR in response, (
            f"{host} did not reject the write as read-only: {response!r}"
        )
