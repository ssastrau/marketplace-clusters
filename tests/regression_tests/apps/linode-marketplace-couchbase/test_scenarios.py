from playwright.sync_api import expect

from regression_tests.pages.couchbase.couchbase_buckets_page import CouchbaseBucketsPage
from regression_tests.pages.couchbase.couchbase_dashboard_page import CouchbaseDashboardPage
from regression_tests.pages.couchbase.couchbase_login_page import CouchbaseLoginPage
from regression_tests.pages.couchbase.couchbase_servers_page import CouchbaseServersPage

EXPECTED_CLUSTER_SIZE = 3


def test_couchbase_startup(context, base_url):
    # Verifies that Couchbase started and the sign-in page loads successfully.
    login_page = CouchbaseLoginPage(context)
    login_page.navigate(base_url)
    expect(context, "Couchbase is not started").to_have_title("Couchbase Server")
    expect(login_page.username_input, "Sign-in form did not render on the screen.").to_be_visible()


def test_couchbase_login(context, base_url, admin_credentials):
    # Verifies that the Administrator can log in with the provided credentials.
    username, password = admin_credentials
    login_page = CouchbaseLoginPage(context)
    login_page.navigate(base_url)
    login_page.login(username, password)

    dashboard_page = CouchbaseDashboardPage(context)
    expect(dashboard_page.user_menu, "User menu did not appear after login.").to_be_visible()
    expect(dashboard_page.user_menu, "Logged-in user is not Administrator.").to_contain_text(
        username
    )


def test_couchbase_dashboard_loads(context, base_url, admin_credentials):
    # Verifies that the cluster dashboard renders with its node summary after login.
    username, password = admin_credentials
    login_page = CouchbaseLoginPage(context)
    login_page.navigate(base_url)
    login_page.login(username, password)

    dashboard_page = CouchbaseDashboardPage(context)
    expect(dashboard_page.page_heading, "Dashboard heading did not render.").to_contain_text(
        "Dashboard"
    )
    expect(
        dashboard_page.active_nodes,
        "Dashboard did not report the expected number of active nodes.",
    ).to_contain_text(f"{EXPECTED_CLUSTER_SIZE} active nodes", timeout=60000)
    expect(
        dashboard_page.failed_over_nodes, "Dashboard reports failed-over nodes."
    ).to_contain_text("0 failed-over nodes")
    expect(dashboard_page.inactive_nodes, "Dashboard reports inactive nodes.").to_contain_text(
        "0 inactive nodes"
    )


def test_couchbase_create_bucket(context, base_url, admin_credentials):
    # Verifies that a new data bucket can be created from the Buckets page.
    username, password = admin_credentials
    login_page = CouchbaseLoginPage(context)
    login_page.navigate(base_url)
    login_page.login(username, password)

    buckets_page = CouchbaseBucketsPage(context)
    buckets_page.navigate_to_buckets()
    expect(buckets_page.page_heading, "Buckets page did not open.").to_contain_text("Buckets")

    bucket_name = "test-playwright-bucket"
    buckets_page.create_bucket(bucket_name)

    expect(
        buckets_page.bucket_rows,
        "Newly created bucket did not appear in the buckets list.",
    ).to_contain_text(bucket_name, timeout=60000)


def test_couchbase_servers_cluster_is_healthy(context, base_url, admin_credentials):
    # Verifies that every cluster node is listed on the Servers page as healthy and active.
    username, password = admin_credentials
    login_page = CouchbaseLoginPage(context)
    login_page.navigate(base_url)
    login_page.login(username, password)

    servers_page = CouchbaseServersPage(context)
    servers_page.navigate_to_servers()
    expect(servers_page.page_heading, "Servers page did not open.").to_contain_text("Servers")

    expect(
        servers_page.server_rows,
        "Servers page does not list the whole cluster.",
    ).to_have_count(EXPECTED_CLUSTER_SIZE, timeout=60000)
    expect(
        servers_page.healthy_server_rows,
        "Not every cluster node is healthy and active.",
    ).to_have_count(EXPECTED_CLUSTER_SIZE)
