from playwright.sync_api import expect

from regression_tests.pages.jitsi.jitsi_landing_page import JitsiLandingPage
from regression_tests.pages.jitsi.jitsi_meeting_page import JitsiMeetingPage
from regression_tests.pages.jitsi.jitsi_prejoin_page import JitsiPrejoinPage

EXPECTED_BRIDGE_COUNT = 3


def test_jitsi_startup(context, base_url):
    # Verifies that Jitsi started and the landing page loads successfully.
    landing_page = JitsiLandingPage(context)
    landing_page.navigate(base_url)
    expect(context, "Jitsi Meet is not started").to_have_title("Jitsi Meet")
    expect(landing_page.heading, "Jitsi Meet heading did not render.").to_be_visible()
    expect(landing_page.meeting_name_input, "Meeting name input did not render.").to_be_visible()
    expect(landing_page.start_meeting_button, "Start meeting button did not render.").to_be_visible()


def test_jitsi_join_meeting(context, base_url):
    # Verifies that a user can start a meeting and join the room.
    landing_page = JitsiLandingPage(context)
    landing_page.navigate(base_url)
    landing_page.start_meeting("test-regression-room")

    prejoin_page = JitsiPrejoinPage(context)
    expect(prejoin_page.prejoin_screen, "Pre-join screen did not load.").to_be_visible(timeout=60000)
    prejoin_page.join("Test User")

    meeting_page = JitsiMeetingPage(context)
    expect(meeting_page.leave_meeting_button, "Meeting room did not load.").to_be_visible(
        timeout=60000
    )
    # The filmstrip is hidden while you are alone in the room, so the toolbar is the
    # landmark that a meeting is actually in progress.
    expect(meeting_page.participants_button, "Meeting toolbar did not render.").to_be_visible()


def test_jitsi_all_bridges_registered(jitsi_service):
    # Verifies that every videobridge joined the brewery MUC and is usable by jicofo.
    selector = jitsi_service.get_bridge_selector()

    assert selector["bridge_count"] == EXPECTED_BRIDGE_COUNT, (
        f"jicofo sees {selector['bridge_count']} videobridges, expected {EXPECTED_BRIDGE_COUNT}."
    )
    assert selector["operational_bridge_count"] == EXPECTED_BRIDGE_COUNT, (
        f"Only {selector['operational_bridge_count']} videobridges are operational, "
        f"expected {EXPECTED_BRIDGE_COUNT}."
    )
    assert selector["lost_bridges"] == 0, (
        f"jicofo lost {selector['lost_bridges']} videobridges since startup."
    )

    bridges = jitsi_service.get_bridges()
    assert len(bridges) == EXPECTED_BRIDGE_COUNT, (
        f"Registered videobridges are {sorted(bridges)}, expected {EXPECTED_BRIDGE_COUNT} of them."
    )


def test_jitsi_conference_is_distributed_across_bridges(context, base_url, jitsi_service):
    # Verifies that a meeting with two participants is carried by more than one
    # videobridge, which is what the cluster exists to do. Jicofo allocates no bridge
    # for a lone participant, so a second one is required to exercise the cluster.
    room = "test-regression-cluster-room"

    landing_page = JitsiLandingPage(context)
    landing_page.navigate(base_url)
    landing_page.start_meeting(room)
    JitsiPrejoinPage(context).join("First User")
    JitsiMeetingPage(context).wait_until_joined()

    second_tab = landing_page.open_new_tab()
    second_prejoin = JitsiPrejoinPage(second_tab)
    second_prejoin.navigate(f"{base_url}/{room}")
    second_prejoin.join("Second User")
    JitsiMeetingPage(second_tab).wait_until_joined()

    stats = jitsi_service.wait_for_conference_of_size(2)
    assert stats["conferences"] >= 1, "jicofo reports no conference for the joined meeting."
    assert stats["largest_conference"] >= 2, (
        f"The meeting has {stats['largest_conference']} participant(s) according to jicofo, "
        "expected both to have joined."
    )

    bridges_in_use = jitsi_service.wait_for_bridges_carrying_endpoints(2)
    assert len(bridges_in_use) >= 2, (
        f"The conference is carried by {bridges_in_use or 'no bridges'}; "
        "expected it to be split across at least 2 videobridges."
    )
