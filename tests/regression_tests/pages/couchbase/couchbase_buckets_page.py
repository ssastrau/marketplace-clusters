from playwright.sync_api import Page, expect

from regression_tests.pages.base_page import BasePage


class CouchbaseBucketsPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.page_heading = self.page.locator("h1")
        self.buckets_nav_link = self.page.locator("nav.nav-sidebar a[href^='#/buckets']")
        self.add_bucket_button = self.page.locator("div.header-controls > a")
        self.bucket_name_input = self.page.locator(".modal input[formcontrolname='name']")
        self.bucket_ram_quota_input = self.page.locator(".modal input[formcontrolname='ramQuotaMB']")
        self.add_bucket_submit = self.page.locator(".modal button[type='submit']")
        self.bucket_rows = self.page.locator("mn-bucket-item")

    def navigate_to_buckets(self):
        self.buckets_nav_link.click()
        self.add_bucket_button.wait_for(state="visible")

    def create_bucket(self, name: str):
        self.add_bucket_button.click()
        expect(self.bucket_ram_quota_input).not_to_have_value("")
        self.bucket_name_input.fill(name)
        self.add_bucket_submit.click()
        self.page.locator(".modal").wait_for(state="detached")
