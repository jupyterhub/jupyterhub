import asyncio
import time
from functools import partial

import pytest
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tornado.escape import url_escape
from tornado.httputil import url_concat

from jupyterhub.tests.selenium.locators import (
    HomePageLocators,
    LoginPageLocators,
    TokenPageLocators,
)
from jupyterhub.utils import exponential_backoff

from ...utils import url_path_join
from ..utils import public_host, public_url, ujoin

pytestmark = pytest.mark.selenium


async def webdriver_wait(driver, condition, timeout=30):
    """an async wrapper for selenium's wait function,
    a condition is something from selenium's expected_conditions"""

    return await exponential_backoff(
        partial(condition, driver),
        timeout=timeout,
        fail_message=f"WebDriver condition not met: {condition}",
    )


def in_thread(f, *args, **kwargs):
    """Run a function in a background thread

    via current event loop's run_in_executor

    Returns asyncio.Future
    """

    return asyncio.get_event_loop().run_in_executor(None, partial(f, *args, **kwargs))


async def open_url(app, browser, url="login"):
    """initiating open the login page in the browser"""

    url = url_path_join(public_host(app), app.hub.base_url, url)
    await in_thread(browser.get, url)
    return url


def click(browser, by_locator):
    """wait for element to be visible, then click on it"""

    WebDriverWait(browser, 10).until(
        EC.visibility_of_element_located(by_locator)
    ).click()


def is_displayed(browser, by_locator):
    """Whether the element is visible or not"""

    return (
        WebDriverWait(browser, 10)
        .until(EC.visibility_of_element_located(by_locator))
        .is_displayed()
    )


def send_text(browser, by_locator, text):
    """wait for element to be presented, then put the text in it"""

    return (
        WebDriverWait(browser, 10)
        .until(EC.presence_of_element_located(by_locator))
        .send_keys(text)
    )


def clear(browser, by_locator):
    """wait for element to be presented, then clear the text in it"""

    return (
        WebDriverWait(browser, 10)
        .until(EC.presence_of_element_located(by_locator))
        .clear()
    )


# LOGIN PAGE
async def test_elements_of_login_page(app, browser):
    await open_url(app, browser)
    logo = is_displayed(browser, LoginPageLocators.LOGO)
    logo_text = browser.find_element(*LoginPageLocators.LOGO).get_attribute("innerHTML")
    assert logo == True


async def login(browser, user, pass_w):
    # fill in username field
    send_text(browser, LoginPageLocators.ACCOUNT, user)
    # fill in password field
    send_text(browser, LoginPageLocators.PASSWORD, pass_w)
    # click submit button
    click(browser, LoginPageLocators.LOGIN_BUTTON)
    await webdriver_wait(browser, EC.url_changes(browser.current_url))


async def test_submit_login_form(app, browser):
    user = "test_user"
    pass_w = "test_user"

    await open_url(app, browser, url="login")
    redirected_url = ujoin(public_url(app), f"/user/{user}/")
    await login(browser, user, pass_w)
    # verify url contains username
    if f"/user/{user}/" not in browser.current_url:
        await webdriver_wait(browser, EC.url_to_be(redirected_url))
    else:
        pass
    assert browser.current_url == redirected_url


@pytest.mark.parametrize(
    'url, params, redirected_url, form_action',
    [
        (
            # spawn?param=value
            # will encode given parameters for an unauthenticated URL in the next url
            # the next parameter will contain the app base URL (replaces BASE_URL in tests)
            'spawn',
            [('param', 'value')],
            '/hub/login?next={{BASE_URL}}hub%2Fspawn%3Fparam%3Dvalue',
            '/hub/login?next={{BASE_URL}}hub%2Fspawn%3Fparam%3Dvalue',
        ),
        (
            # login?param=fromlogin&next=encoded(/hub/spawn?param=value)
            # will drop parameters given to the login page, passing only the next url
            'login',
            [('param', 'fromlogin'), ('next', '/hub/spawn?param=value')],
            '/hub/login?param=fromlogin&next=%2Fhub%2Fspawn%3Fparam%3Dvalue',
            '/hub/login?next=%2Fhub%2Fspawn%3Fparam%3Dvalue',
        ),
        (
            # login?param=value&anotherparam=anothervalue
            # will drop parameters given to the login page, and use an empty next url
            'login',
            [('param', 'value'), ('anotherparam', 'anothervalue')],
            '/hub/login?param=value&anotherparam=anothervalue',
            '/hub/login?next=',
        ),
        (
            # login
            # simplest case, accessing the login URL, gives an empty next url
            'login',
            [],
            '/hub/login',
            '/hub/login?next=',
        ),
    ],
)
async def test_open_url_login(
    app,
    browser,
    url,
    params,
    redirected_url,
    form_action,
    user='test_user',
    pass_w='test_user',
):
    url = url_path_join(public_host(app), app.hub.base_url, url)
    url_new = url_concat(url, params)
    await in_thread(browser.get, url_new)
    redirected_url = redirected_url.replace('{{BASE_URL}}', url_escape(app.base_url))
    form_action = form_action.replace('{{BASE_URL}}', url_escape(app.base_url))
    form = browser.find_element(*LoginPageLocators.FORM_LOGIN).get_attribute('action')

    # verify title / url
    assert browser.title == LoginPageLocators.PAGE_TITLE
    assert form.endswith(form_action)
    # login in with params
    await login(browser, user, pass_w)
    # verify next url + params
    next_url = browser.current_url
    if url_escape(app.base_url) in form_action:
        assert next_url.endswith("param=value")
    elif "next=%2Fhub" in form_action:
        assert next_url.endswith("spawn?param=value")
        assert f"user/{user}/" not in next_url
    else:
        if next_url.endswith(f"/user/{user}/") == False:
            await webdriver_wait(
                browser, EC.url_to_be(ujoin(public_url(app), f"/user/{user}/"))
            )
        assert next_url.endswith(f"/user/{user}/")


@pytest.mark.parametrize(
    "user, pass_w",
    [
        (" ", ""),
        ("user", ""),
        (" ", "password"),
        ("user", "password"),
    ],
)
async def test_invalid_credantials(app, browser, user, pass_w):
    await open_url(app, browser)
    await login(browser, user, pass_w)
    await asyncio.sleep(0.1)
    """adding for a catching of the reflected error"""
    try:
        error = browser.find_element(*LoginPageLocators.ERROR_INVALID_CREDANTIALS)
        await webdriver_wait(browser, EC.visibility_of(error))
    except NoSuchElementException:
        error = None

    # verify error message and url still eguals to the login page
    assert LoginPageLocators.ERROR_MESSAGES_LOGIN == error.text
    assert 'hub/login' in browser.current_url


# HOME PAGE
async def open_home_page(app, browser, user="test_user", pass_w="test_user"):
    url = url_path_join(public_host(app), app.hub.base_url, "/login?next=/hub/home")
    await in_thread(browser.get, url)
    redirected_url = url_path_join(public_host(app), app.base_url, '/hub/home')
    await login(browser, user, pass_w)
    await in_thread(browser.get, redirected_url)


# TOKEN PAGE
async def open_token_page(app, browser, user="test_user", pass_w="test_user"):

    url = url_path_join(public_host(app), app.hub.base_url, "/login?next=/hub/token")
    await in_thread(browser.get, url)
    redirected_url = url_path_join(public_host(app), app.base_url, '/hub/token')
    await login(browser, user, pass_w)
    await in_thread(browser.get, redirected_url)
