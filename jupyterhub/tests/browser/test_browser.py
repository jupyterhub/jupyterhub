"""Tests for the Playwright Python"""

import re

import pytest
from playwright.async_api import expect

from jupyterhub.tests.utils import public_host
from jupyterhub.utils import url_path_join

pytestmark = pytest.mark.playwright


async def login(browser, username, password):
    """filling the login form by user and pass_w parameters and iniate the login"""

    await browser.get_by_label("Username:").click()
    await browser.get_by_label("Username:").fill(username)
    await browser.get_by_label("Password:").click()
    await browser.get_by_label("Password:").fill(password)
    await browser.get_by_role("button", name="Sign in").click()


async def test_open_login_page(app, browser):
    login_url = url_path_join(public_host(app), app.hub.base_url, "login")
    await browser.goto(login_url)
    await expect(browser).to_have_url(re.compile(r".*/login"))
    await expect(browser).to_have_title("JupyterHub")
    form = browser.locator('//*[@id="login-main"]/form')
    await expect(form).to_be_visible()
    await expect(form.locator('//h1')).to_have_text("Sign in")
