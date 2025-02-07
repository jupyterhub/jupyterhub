from collections import namedtuple

import pytest
from playwright.async_api import async_playwright

from ..conftest import add_user, new_username

# To debug failures you can pass --headed, --slowmo=<delay>, and --video=on


@pytest.fixture
def cmdoptions(request, pytestconfig):
    # Playwright pytest supplies some CLI arguments, but they're not always taken
    # into account so handle them ourselves
    # https://playwright.dev/python/docs/test-runners#cli-arguments
    print(request.__dict__)
    print(pytestconfig.__dict__)
    return dict(
        # (opt, request.config.getoption(f"--{opt}"))
        (opt, pytestconfig.getoption(f"--{opt}"))
        for opt in ["headed", "output", "slowmo", "video"]
    )


@pytest.fixture()
async def browser(cmdoptions):
    print(cmdoptions)

    # browser_type in ["chromium", "firefox", "webkit"]
    async with async_playwright() as playwright:
        browser = await playwright.firefox.launch(
            headless=not cmdoptions["headed"], slow_mo=cmdoptions["slowmo"]
        )
        context = await browser.new_context(
            record_video_dir=cmdoptions["output"]
            if cmdoptions["video"] != "off"
            else None
        )
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
