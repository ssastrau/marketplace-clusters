import json
import re

MASTER_STATE_URL = "http://localhost:8480/json/"
SPARK_HOME = "/opt/spark"
PI_EXAMPLE_CLASS = "org.apache.spark.examples.SparkPi"

APP_ID_PATTERN = re.compile(r"Connected to Spark cluster with app ID (app-\S+)")
EXECUTOR_PATTERN = re.compile(r"Executor added: \S+ on (worker-\S+)")
PI_RESULT_PATTERN = re.compile(r"Pi is roughly \d+\.\d+")


class SparkService:
    def __init__(self, remote_exec):
        self.remote_exec = remote_exec

    def get_master_state(self) -> dict:
        stdout, stderr, exit_code = self.remote_exec(
            f"curl -s --max-time 15 {MASTER_STATE_URL}", timeout=60
        )
        if exit_code != 0:
            raise RuntimeError(
                f"Request to {MASTER_STATE_URL} failed (exit {exit_code}): {stderr or stdout}"
            )
        return json.loads(stdout)

    def get_workers(self) -> list:
        return self.get_master_state()["workers"]

    def get_alive_workers(self) -> list:
        return [worker for worker in self.get_workers() if worker["state"] == "ALIVE"]

    def run_spark_pi(self, total_executor_cores: int = 2, timeout: int = 300) -> dict:
        master_url = self.get_master_state()["url"]
        command = (
            f"cd {SPARK_HOME} && sudo -u spark ./bin/spark-submit "
            f"--master {master_url} --class {PI_EXAMPLE_CLASS} "
            f"--total-executor-cores {total_executor_cores} "
            f"examples/jars/spark-examples_*.jar 10 2>&1"
        )
        output, _, _ = self.remote_exec(command, timeout=timeout)
        app_id = APP_ID_PATTERN.search(output)
        return {
            "app_id": app_id.group(1) if app_id else None,
            "worker_ids": sorted(set(EXECUTOR_PATTERN.findall(output))),
            "pi_computed": bool(PI_RESULT_PATTERN.search(output)),
            "output": output,
        }
