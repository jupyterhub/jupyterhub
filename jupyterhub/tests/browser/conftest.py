import os
from collections import namedtuple

import pytest
from playwright.async_api import async_playwright, expect
from pytest import CollectReport, StashKey

from ..conftest import add_user, new_username

phase_report_key = StashKey[dict[str, CollectReport]]()


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    rep = yield

    # store test results for each phase of a call, which can
    # be "setup", "call", "teardown"
    item.stash.setdefault(phase_report_key, {})[rep.when] = rep

    return rep


@pytest.fixture(scope="module")
async def _browser():
    # browser_type in ["chromium", "firefox", "webkit"]
    async with async_playwright() as playwright:
        browser = await playwright.firefox.launch(headless=True)
        yield browser


@pytest.fixture
async def browser(request, _browser):
    context = await _browser.new_context()
    # context sets default timeout for a lot of things, but not expect
    context.set_default_timeout(30_000)
    # default timeout for expect
    expect.set_options(timeout=30_000)
    page = await context.new_page()
    yield page
    report = request.node.stash[phase_report_key]
    if "call" in report and report["call"].failed:
        print(f"{page.url=}")
        actions = os.getenv("GITHUB_ACTIONS")
        if actions:
            print("::group::Page HTML")
        print("----- Page HTML -----")
        print(await page.locator("body").inner_html())
        print("----- End Page HTML -----")
        if actions:
            print("::endgroup::")
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
