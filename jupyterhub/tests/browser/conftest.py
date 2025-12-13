from collections import namedtuple

import pytest
from playwright.async_api import async_playwright

from ..conftest import add_user, new_username


# To debug failures you can pass these arguments on the pytest CLI
def pytest_addoption(parser):
    parser.addoption(
        "--headed", action="store_true", default=False, help="Show browser"
    )
    parser.addoption(
        "--slowmo",
        action="store",
        default=0,
        type=int,
        help="Delay each step by this number of milliseconds",
    )
    parser.addoption(
        "--videodir",
        action="store",
        default=None,
        help="Record videos of each test to this directory",
    )


@pytest.fixture
def cmdoptions(request):
    return dict(
        (opt, request.config.getoption(f"--{opt}"))
        for opt in ["headed", "slowmo", "videodir"]
    )


@pytest.fixture()
async def browser(cmdoptions):
    print(cmdoptions)

    # browser_type in ["chromium", "firefox", "webkit"]
    async with async_playwright() as playwright:
        browser = await playwright.firefox.launch(
            headless=not cmdoptions["headed"],
            slow_mo=cmdoptions["slowmo"],
        )
        context = await browser.new_context(record_video_dir=cmdoptions["videodir"])
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
