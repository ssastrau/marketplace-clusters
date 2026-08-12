EXPECTED_CLUSTER_SIZE = 3
EXPECTED_VOTERS = "[1,2,3]"
PROBE_VALUE = "regression_value"


def test_kafka_service_active_and_broker_answers(kafka_service):
    # Verifies that the Kafka unit is running and the broker answers a client request
    assert kafka_service.is_active() == "active", "The Kafka unit is not active."

    brokers = kafka_service.brokers()

    assert brokers, "No broker answered the API-versions request."


def test_kafka_kraft_quorum_has_a_leader(kafka_service):
    # Verifies that the KRaft controller quorum elected a leader and every node is a
    # voter.
    status = kafka_service.quorum_status()

    assert status.get("CurrentVoters") == EXPECTED_VOTERS, (
        f"The controller quorum does not have voters {EXPECTED_VOTERS}: {status}"
    )
    assert status.get("CurrentObservers") == "[]", (
        f"A node is an observer rather than a voter: {status}"
    )
    assert status.get("LeaderId", "").isdigit(), f"The quorum has no elected leader: {status}"
    assert status.get("ClusterId"), f"The quorum reported no cluster id: {status}"


def test_kafka_all_brokers_are_registered(kafka_service):
    # Verifies that every node joined as a broker, which is what separates a cluster from
    # three isolated brokers.
    brokers = kafka_service.brokers()

    assert len(brokers) == EXPECTED_CLUSTER_SIZE, (
        f"Expected {EXPECTED_CLUSTER_SIZE} brokers, found: {brokers}"
    )
    assert sorted(brokers.values()) == ["1", "2", "3"], (
        f"The broker ids are not 1, 2 and 3: {brokers}"
    )


def test_kafka_topic_is_replicated_across_every_broker(kafka_service, unique_topic):
    # Verifies that a replicated topic is fully in sync
    topic = unique_topic

    _, stderr, exit_code = kafka_service.create_topic(topic, EXPECTED_CLUSTER_SIZE, EXPECTED_CLUSTER_SIZE)
    assert exit_code == 0, f"Could not create the topic: {stderr}"

    partitions = kafka_service.describe_topic(topic)

    kafka_service.delete_topic(topic)

    assert len(partitions) == EXPECTED_CLUSTER_SIZE, (
        f"Expected {EXPECTED_CLUSTER_SIZE} partitions, found: {partitions}"
    )
    for partition in partitions:
        in_sync = sorted(partition["isr"].split(","))
        assert in_sync == ["1", "2", "3"], (
            f"Partition {partition['partition']} is under-replicated, in-sync: {partition['isr']}"
        )


def test_kafka_produce_and_consume_roundtrip(kafka_service, unique_topic):
    # Verifies that a message can be published and read back
    topic = unique_topic

    _, stderr, exit_code = kafka_service.create_topic(topic, 1, EXPECTED_CLUSTER_SIZE)
    assert exit_code == 0, f"Could not create the topic: {stderr}"

    _, stderr, exit_code = kafka_service.produce(topic, PROBE_VALUE)
    assert exit_code == 0, f"Could not produce to the topic: {stderr}"

    consumed = kafka_service.consume(topic)

    kafka_service.delete_topic(topic)

    assert PROBE_VALUE in consumed, f"The consumer did not return the message: {consumed!r}"
