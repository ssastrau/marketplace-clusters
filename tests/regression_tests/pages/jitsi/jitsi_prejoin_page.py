from playwright.sync_api import Page

from regression_tests.pages.base_page import BasePage


class JitsiPrejoinPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.prejoin_screen = self.page.locator("[data-testid='prejoin.screen']")
        self.display_name_input = self.page.locator("#premeeting-name-input")
        self.join_button = self.page.locator("[data-testid='prejoin.joinMeeting']")

    def join(self, display_name: str):
        self.display_name_input.wait_for(state="visible", timeout=60000)
        self.display_name_input.fill(display_name)
        self.join_button.click()
