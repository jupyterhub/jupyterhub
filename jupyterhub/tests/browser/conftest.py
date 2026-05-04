from collections import namedtuple

import pytest
from playwright.async_api import async_playwright, expect

from ..conftest import add_user, new_username


@pytest.fixture(scope="module")
async def _browser():
    # browser_type in ["chromium", "firefox", "webkit"]
    async with async_playwright() as playwright:
        browser = await playwright.firefox.launch(headless=True)
        yield browser


@pytest.fixture
async def browser(_browser):
    context = await _browser.new_context()
    # context sets default timeout for a lot of things, but not expect
    context.set_default_timeout(30_000)
    # default timeout for expect
    expect.set_options(timeout=30_000)
    page = await context.new_page()
    yield page
    await context.clear_cookies()
    await context.close()


@pytest.fixture
def user_special_chars(app):
    """Fixture for creating a temporary user with special characters in the name"""
    user = add_user(app.db, app, name=new_username("testuser<'&\">"))
    yield namedtuple('UserSpecialChars', ['user', 'urlname', 'urlname_js'])(
        user,
        user.name.replace("<'&\">", "%3C%27%26%22%3E"),
        # Sometimes the URL only has partial escaping
        user.name.replace("<'&\">", "%3C'&%22%3E"),
    )
