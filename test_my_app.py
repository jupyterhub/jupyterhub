import re

from playwright.sync_api import Page, expect


def test_homepage_has_JupyterHub_in_title_and_Sign_in_button(page: Page):
    # Open login page
    page.goto('http://localhost:8000/hub/login')

    # Expect the title to be contain the string JupyterHub
    expect(page).to_have_title(re.compile("JupyterHub"))

    # Select sign-in button using its class
    sign_in = page.query_selector(".btn-jupyter")

    # Click on sign-in button
    sign_in.click()

    # Expect the URL to contain next
    expect(page).to_have_url(re.compile(".*next"))
