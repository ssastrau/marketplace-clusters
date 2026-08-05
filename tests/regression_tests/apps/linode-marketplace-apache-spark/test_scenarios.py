import re

from playwright.sync_api import expect

from regression_tests.pages.spark.spark_master_page import SparkMasterPage

EXPECTED_WORKER_COUNT = 2
TOTAL_EXECUTOR_CORES = EXPECTED_WORKER_COUNT


def test_spark_startup(context, base_url):
    # Verifies that the Spark master started and its UI loads successfully.
    master_page = SparkMasterPage(context)
    master_page.navigate(base_url)
    expect(context, "Spark master UI is not started").to_have_title(
        re.compile(r"^Spark Master at spark://")
    )
    expect(master_page.status, "Spark master is not ALIVE.").to_have_text("Status: ALIVE")
    expect(master_page.workers_table, "Workers table did not render.").to_be_visible()


def test_spark_ui_requires_basic_auth(http_session, base_url, spark_ui_credentials):
    # Verifies that nginx protects the master UI. This app has no login form, so
    # Basic Auth is what stands between the internet and the cluster.
    username, password = spark_ui_credentials

    unauthenticated = http_session.get(base_url)
    assert unauthenticated.status_code == 401, (
        f"The master UI returned {unauthenticated.status_code} without credentials, "
        "expected 401 - it is not protected."
    )

    authenticated = http_session.get(base_url, auth=(username, password))
    assert authenticated.status_code == 200, (
        f"The master UI returned {authenticated.status_code} with valid credentials, expected 200."
    )
    assert "Spark Master at" in authenticated.text, (
        "The authenticated response did not come from the Spark master UI."
    )


def test_spark_all_workers_registered(context, base_url):
    # Verifies that every worker node joined the master and is usable.
    master_page = SparkMasterPage(context)
    master_page.navigate(base_url)

    expect(master_page.alive_workers, "The master does not see the whole cluster.").to_have_text(
        f"Alive Workers: {EXPECTED_WORKER_COUNT}"
    )
    expect(master_page.worker_state_cells, "Not every worker is ALIVE.").to_have_text(
        ["ALIVE"] * EXPECTED_WORKER_COUNT
    )


def test_spark_cluster_resources_are_pooled(context, base_url, spark_service):
    # Verifies that the master offers the workers' combined cores rather than a single
    # node's, which is the point of running a cluster.
    pooled_cores = sum(worker["cores"] for worker in spark_service.get_alive_workers())

    master_page = SparkMasterPage(context)
    master_page.navigate(base_url)
    expect(master_page.cores_in_use, "The UI does not show the pooled cores.").to_contain_text(
        f"{pooled_cores} Total"
    )


def test_spark_job_runs_across_the_cluster(context, base_url, spark_service):
    # Verifies that a real job is accepted, distributed to the workers and completed.
    result = spark_service.run_spark_pi(total_executor_cores=TOTAL_EXECUTOR_CORES)

    assert result["pi_computed"], (
        "SparkPi did not produce a result. Last lines of the submit output:\n"
        f"{result['output'][-1500:]}"
    )
    assert len(result["worker_ids"]) > 1, (
        f"The job ran executors on {result['worker_ids'] or 'no workers'}; "
        "expected it to be spread across more than one worker."
    )
    assert result["app_id"], "The submit output did not report an application id."

    master_page = SparkMasterPage(context)
    master_page.navigate(base_url)
    expect(
        master_page.completed_app_row(result["app_id"]),
        f"Application {result['app_id']} is not in Completed Applications.",
    ).to_be_visible()
    expect(
        master_page.completed_app_cores(result["app_id"]),
        f"The master granted the wrong number of cores to {result['app_id']}.",
    ).to_have_text(str(TOTAL_EXECUTOR_CORES))
