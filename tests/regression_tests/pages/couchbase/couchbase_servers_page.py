from playwright.sync_api import Page

from regression_tests.pages.base_page import BasePage


class CouchbaseServersPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.page_heading = self.page.locator("h1")
        self.servers_nav_link = self.page.locator("nav.nav-sidebar a[href^='#/servers']")
        self.server_rows = self.page.locator("div.cbui-tablerow.dynamic_active")
        self.healthy_server_rows = self.page.locator(
            "div.cbui-tablerow.dynamic_healthy.dynamic_active"
        )
        self.rebalance_button = self.page.locator("div.server-actions button")

    def navigate_to_servers(self):
        self.servers_nav_link.click()
        self.server_rows.first.wait_for(state="visible")
