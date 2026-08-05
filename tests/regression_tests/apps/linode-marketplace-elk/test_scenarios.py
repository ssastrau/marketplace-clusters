from playwright.sync_api import expect

from regression_tests.pages.elk.elk_home_page import ElkHomePage
from regression_tests.pages.elk.elk_index_management_page import ElkIndexManagementPage
from regression_tests.pages.elk.elk_login_page import ElkLoginPage

EXPECTED_ELASTICSEARCH_NODES = 2


def test_elk_startup(context, base_url):
    # Verifies that Kibana started and the login page loads successfully.
    login_page = ElkLoginPage(context)
    login_page.navigate(base_url)
    expect(context, "Kibana is not started").to_have_title("Elastic")
    expect(login_page.username_input, "Login form did not render on the screen.").to_be_visible(
        timeout=30000
    )


def test_elk_login(context, base_url, elastic_credentials):
    # Verifies that the elastic superuser can log in with the provided credentials.
    username, password = elastic_credentials
    login_page = ElkLoginPage(context)
    login_page.navigate(base_url)
    login_page.login(username, password)

    home_page = ElkHomePage(context)
    expect(home_page.global_nav, "Kibana did not load after login.").to_be_visible(timeout=60000)
    expect(context, "Kibana did not land on the home page after login.").to_have_title(
        "Home - Elastic", timeout=60000
    )


def test_elk_index_management_loads(context, base_url, elastic_credentials):
    # Verifies that the Index Management page renders its indices table.
    username, password = elastic_credentials
    login_page = ElkLoginPage(context)
    login_page.navigate(base_url)
    login_page.login(username, password)

    index_page = ElkIndexManagementPage(context)
    index_page.navigate_to_index_management(base_url)
    expect(index_page.page_heading, "Index Management page did not open.").to_contain_text(
        "Index Management"
    )
    expect(index_page.index_table, "Indices table did not render.").to_be_visible()


def test_elk_create_index(context, base_url, elastic_credentials):
    # Verifies that a new Elasticsearch index can be created from Kibana.
    username, password = elastic_credentials
    login_page = ElkLoginPage(context)
    login_page.navigate(base_url)
    login_page.login(username, password)

    index_page = ElkIndexManagementPage(context)
    index_page.navigate_to_index_management(base_url)

    index_name = "test-playwright-index"
    index_page.create_index(index_name)

    expect(
        index_page.index_name_links,
        "Newly created index did not appear in the indices table.",
    ).to_contain_text(index_name, timeout=60000)


def test_elk_kibana_api_status_is_available(elk_service):
    # Verifies over HTTP that Kibana is serving and its Elasticsearch link is up.
    status = elk_service.get_kibana_status()

    overall = status["status"]["overall"]["level"]
    assert overall == "available", f"Kibana reports overall status '{overall}', expected 'available'."

    elasticsearch = status["status"]["core"]["elasticsearch"]["level"]
    assert elasticsearch == "available", (
        f"Kibana cannot reach Elasticsearch: core status is '{elasticsearch}'."
    )


def test_elk_cluster_is_healthy(elk_service):
    # Verifies that every Elasticsearch node joined and the cluster is green.
    health = elk_service.get_cluster_health()

    assert health["status"] == "green", (
        f"Elasticsearch cluster status is '{health['status']}', expected 'green'."
    )
    assert health["number_of_nodes"] == EXPECTED_ELASTICSEARCH_NODES, (
        f"Cluster has {health['number_of_nodes']} nodes, expected {EXPECTED_ELASTICSEARCH_NODES}."
    )
