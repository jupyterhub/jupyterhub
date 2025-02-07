from collections import namedtuple
from os import getenv

import pytest
from playwright.async_api import async_playwright

from ..conftest import add_user, new_username

# To debug failures set environment variables
# TEST_HEADLESS=0 to display the browser whilst the tests are run
# TEST_SLOWMO=<delay in milliseconds> to pause between each step
# TEST_VIDEODIR=video-dir/ to save videos of tests


@pytest.fixture()
async def browser():
    TEST_HEADLESS = getenv("TEST_HEADLESS", "1") == "1"
    TEST_SLOWMO = int(getenv("TEST_SLOWMO", "0"))
    TEST_VIDEODIR = getenv("TEST_VIDEODIR")

    # browser_type in ["chromium", "firefox", "webkit"]
    async with async_playwright() as playwright:
        browser = await playwright.firefox.launch(
            headless=TEST_HEADLESS, slow_mo=TEST_SLOWMO
        )
        context = await browser.new_context(record_video_dir=TEST_VIDEODIR)
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
