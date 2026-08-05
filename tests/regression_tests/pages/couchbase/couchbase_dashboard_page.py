from playwright.sync_api import Page

from regression_tests.pages.base_page import BasePage


class CouchbaseDashboardPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.page_heading = self.page.locator("h1")
        self.user_menu = self.page.locator("nav.nav-header a.dropdown-toggle").last
        self.active_nodes = self.page.locator("div.dashboard-node[title='active nodes']")
        self.failed_over_nodes = self.page.locator("div.dashboard-node[title='failed-over nodes']")
        self.inactive_nodes = self.page.locator("div.dashboard-node[title='inactive nodes']")
        self.servers_nav_link = self.page.locator("nav.nav-sidebar a[href^='#/servers']")
        self.buckets_nav_link = self.page.locator("nav.nav-sidebar a[href^='#/buckets']")
