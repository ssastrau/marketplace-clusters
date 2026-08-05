import json
import time

JICOFO_STATS_URL = "http://localhost:8888/stats"
JICOFO_DEBUG_URL = "http://localhost:8888/debug"


class JitsiService:
    def __init__(self, remote_exec):
        self.remote_exec = remote_exec

    def _get_json(self, url: str) -> dict:
        stdout, stderr, exit_code = self.remote_exec(f"curl -s --max-time 15 {url}", timeout=60)
        if exit_code != 0:
            raise RuntimeError(f"Request to {url} failed (exit {exit_code}): {stderr or stdout}")
        return json.loads(stdout)

    def get_stats(self) -> dict:
        return self._get_json(JICOFO_STATS_URL)

    def get_bridge_selector(self) -> dict:
        return self.get_stats()["bridge_selector"]

    def get_bridges(self) -> dict:
        bridges = self._get_json(JICOFO_DEBUG_URL)["bridge_selector"]["bridge"]
        return {jid.rsplit("/", 1)[-1]: stats for jid, stats in bridges.items()}

    def bridges_carrying_endpoints(self) -> list:
        return [name for name, stats in self.get_bridges().items() if stats.get("endpoints", 0) > 0]

    def wait_for_conference_of_size(self, size: int, timeout: int = 90) -> dict:
        deadline = time.monotonic() + timeout
        stats = self.get_stats()
        while time.monotonic() < deadline and stats.get("largest_conference", 0) < size:
            time.sleep(5)
            stats = self.get_stats()
        return stats

    def wait_for_bridges_carrying_endpoints(self, count: int, timeout: int = 90) -> list:
        deadline = time.monotonic() + timeout
        in_use = self.bridges_carrying_endpoints()
        while time.monotonic() < deadline and len(in_use) < count:
            time.sleep(5)
            in_use = self.bridges_carrying_endpoints()
        return in_use
