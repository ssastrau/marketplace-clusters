from playwright.sync_api import Page

from regression_tests.pages.base_page import BasePage


class ElkHomePage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.global_nav = self.page.locator("[data-test-subj='headerGlobalNav']")
        self.nav_toggle_button = self.page.locator("[data-test-subj='toggleNavButton']")
        self.spaces_nav_selector = self.page.locator("[data-test-subj='spacesNavSelector']")
