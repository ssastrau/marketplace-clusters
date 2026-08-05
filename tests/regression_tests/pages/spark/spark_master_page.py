from playwright.sync_api import Page

from regression_tests.pages.base_page import BasePage


class SparkMasterPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.alive_workers = self._summary_item("Alive Workers:")
        self.cores_in_use = self._summary_item("Cores in use:")
        self.status = self._summary_item("Status:")
        self.workers_table = self.page.locator(".aggregated-workers table")
        self.worker_state_cells = self.page.locator(
            ".aggregated-workers table tbody tr td:nth-child(3)"
        )
        self.completed_app_rows = self.page.locator(
            ".aggregated-completedApps table tbody tr"
        )

    def _summary_item(self, label: str):
        return self.page.locator(f"li:has(strong:text-is('{label}'))")

    def completed_app_row(self, app_id: str):
        return self.completed_app_rows.filter(has_text=app_id)

    def completed_app_cores(self, app_id: str):
        return self.completed_app_row(app_id).locator("td:nth-child(3)")
