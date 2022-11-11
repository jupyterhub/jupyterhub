import asyncio
from functools import partial

import pytest
from selenium import webdriver

from ..utils import url_path_join
from .utils import public_host


@pytest.fixture
def in_thread():
    """Run a function in a background thread.

    via current event loop's run_in_executor

    Returns asyncio.Future
    """

    def submit(f, *args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(
            None, partial(f, *args, **kwargs)
        )

    return submit


@pytest.fixture
def browser():
    driver = webdriver.Firefox()
    yield driver
    driver.close()
    driver.quit()


async def test_check(app, browser, in_thread):
    url = url_path_join(public_host(app), app.hub.base_url, "login")
    await in_thread(browser.get, url)

    assert browser.title == "Project Jupyter | JupyterHub"
    print("Test completed")
