from playwright.sync_api import Page

from regression_tests.pages.base_page import BasePage

INDEX_MANAGEMENT_PATH = "/app/management/data/index_management/indices"


class ElkIndexManagementPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.page_heading = self.page.locator("h1")
        self.index_table = self.page.locator("[data-test-subj='indexTable']")
        self.index_name_links = self.page.locator("[data-test-subj='indexTableIndexNameLink']")
        self.create_index_button = self.page.locator("[data-test-subj='createIndexButton']")
        self.index_name_input = self.page.locator("[data-test-subj='createIndexNameFieldText']")
        self.create_index_submit = self.page.locator("[data-test-subj='createIndexSaveButton']")

    def navigate_to_index_management(self, base_url: str):
        self.navigate(f"{base_url}{INDEX_MANAGEMENT_PATH}")
        self.index_table.wait_for(state="visible", timeout=60000)

    def create_index(self, name: str):
        self.create_index_button.first.click()
        self.index_name_input.wait_for(state="visible")
        self.index_name_input.fill(name)
        self.create_index_submit.click()
        self.page.locator("[role='dialog']").wait_for(state="detached")
