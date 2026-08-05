from playwright.sync_api import Page

from regression_tests.pages.base_page import BasePage


class JitsiMeetingPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.toggle_filmstrip_button = self.page.locator("#toggleFilmstripButton")
        self.leave_meeting_button = self.page.locator("[aria-label='Leave the meeting']")
        self.participants_button = self.page.locator("[aria-label^='Open participants panel']")

    def wait_until_joined(self):
        self.leave_meeting_button.wait_for(state="visible", timeout=60000)
