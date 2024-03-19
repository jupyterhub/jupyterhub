from collections import namedtuple

import pytest
from playwright.async_api import async_playwright

from ..conftest import add_user, new_username


@pytest.fixture()
async def browser():
    # browser_type in ["chromium", "firefox", "webkit"]
    async with async_playwright() as playwright:
        browser = await playwright.firefox.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        yield page
        await context.clear_cookies()
        await browser.close()


@pytest.fixture
def user_special_chars(app):
    """Fixture for creating a temporary user with special characters in the name"""
    user = add_user(app.db, app, name=new_username("testuser<'&\">"))
    yield namedtuple('UserSpecialChars', ['user', 'urlname'])(
        user,
        user.name.replace("<'&\">", "%3C%27%26%22%3E"),
    )
