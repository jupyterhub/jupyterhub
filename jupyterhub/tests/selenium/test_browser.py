import asyncio
import pickle
import pprint
import time
from functools import partial
from operator import contains
from pprint import pprint
from termios import TABDLY
from traceback import format_stack
from urllib.parse import urlencode, urlparse

import pytest
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tornado.escape import url_escape
from tornado.httputil import url_concat

from jupyterhub.tests.conftest import admin_user
from jupyterhub.tests.selenium.locators import (
    HomePageLocators,
    LoginPageLocators,
    TokenPageLocators,
)
from jupyterhub.utils import exponential_backoff

from ...utils import url_escape_path, url_path_join
from ..utils import async_requests, get_page, public_host, public_url, ujoin

pytestmark = pytest.mark.selenium


async def webdriver_wait(driver, condition, timeout=30):
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


async def open_url(app, browser):

    url = url_path_join(public_host(app), app.hub.base_url, "login")
    await in_thread(browser.get, url)
    return url


def click(browser, by_locator):
    WebDriverWait(browser, 10).until(
        EC.visibility_of_element_located(by_locator)
    ).click()


def is_displayed(browser, by_locator):
    return (
        WebDriverWait(browser, 10)
        .until(EC.visibility_of_element_located(by_locator))
        .is_displayed()
    )


def send_text(browser, by_locator, text):
    return (
        WebDriverWait(browser, 10)
        .until(EC.presence_of_element_located(by_locator))
        .send_keys(text)
    )


def clear(browser, by_locator):
    return (
        WebDriverWait(browser, 10)
        .until(EC.presence_of_element_located(by_locator))
        .clear()
    )


def element(browser, by_locator):
    WebDriverWait(browser, 10).until(EC.visibility_of_element_located(by_locator))


def delete_cookies(browser, domains=None):

    if domains is not None:
        cookies = browser.get_cookies()
        original_len = len(cookies)
        for cookie in cookies:
            if str(cookie["domain"]) in domains:
                cookies.remove(cookie)
        if len(cookies) < original_len:  # if cookies changed, we will update them
            # deleting everything and adding the modified cookie object
            browser.delete_all_cookies()
            for cookie in cookies:
                browser.add_cookie(cookie)
    else:
        browser.delete_all_cookies()


# LOGIN PAGE
async def test_elements_of_login_page(app, browser):
    await open_url(app, browser)
    logo = is_displayed(browser, LoginPageLocators.LOGO)
    logo_text = browser.find_element(*LoginPageLocators.LOGO).get_attribute("innerHTML")
    """TBD"""
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

    await open_url(app, browser)
    redirected_url = ujoin(public_url(app), f"/user/{user}/")
    await login(browser, user, pass_w)
    # verify url contains username
    if f"/user/{user}/" not in browser.current_url:
        webdriver_wait(browser, EC.url_to_be(redirected_url))
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
async def test_open_url_login(app, browser, url, params, redirected_url, form_action):
    url = url_path_join(public_host(app), app.hub.base_url, url)
    url_new = url_concat(url, params)
    await in_thread(browser.get, url_new)
    redirected_url = redirected_url.replace('{{BASE_URL}}', url_escape(app.base_url))
    form_action = form_action.replace('{{BASE_URL}}', url_escape(app.base_url))
    form = browser.find_element(*LoginPageLocators.FORM_LOGIN).get_attribute('action')

    print("Link in form: " + form)
    # verify title / url
    assert browser.title == LoginPageLocators.PAGE_TITLE
    assert form.endswith(form_action)
    print("Current Link in form: " + browser.current_url)
    # login in with params
    await login(browser, user='test_user', pass_w='test_user')
    # verify next url + params
    user = 'test_user'
    next_url = browser.current_url
    if url_escape(app.base_url) in form_action:
        print("Current Link 2: " + browser.current_url)
        assert next_url.endswith("param=value")
    elif "next=%2Fhub" in form_action:
        assert next_url.endswith("spawn?param=value")
        assert f"user/{user}/" not in next_url
        print("Current Link 2: " + browser.current_url)
    else:
        if next_url.endswith(f"/user/{user}/") == False:
            webdriver_wait(
                browser, EC.url_to_be(ujoin(public_url(app), f"/user/{user}/"))
            )
        assert next_url.endswith(f"/user/{user}/")
        print("Current Link 2: " + browser.current_url)


"""TBD"""


@pytest.mark.parametrize(
    'running, next_url, location, params',
    [
        # default URL if next not specified, for both running and not
        (True, '', '', None),
        (False, '', '', None),
        # next_url is respected
        (False, '/hub/admin', '/hub/admin', None),
        (False, '/user/other', '/hub/user/other', None),
        (False, '/absolute', '/absolute', None),
        (False, '/has?query#andhash', '/has?query#andhash', None),
        # :// in query string or fragment
        (False, '/has?repo=https/host.git', '/has?repo=https/host.git', None),
        (False, '/has?repo=https://host.git', '/has?repo=https://host.git', None),
        (False, '/has#repo=https://host.git', '/has#repo=https://host.git', None),
        # next_url outside is not allowed
        (False, 'relative/path', '', None),
        (False, 'https://other.domain', '', None),
        (False, 'ftp://other.domain', '', None),
        (False, '//other.domain', '', None),
        (False, '///other.domain/triple', '', None),
        (False, '\\\\other.domain/backslashes', '', None),
        # params are handled correctly (ignored if ?next= specified)
        (
            True,
            '/hub/admin?left=1&right=2',
            'hub/admin?left=1&right=2',
            {"left": "abc"},
        ),
        (False, '/hub/admin', 'hub/admin', [('left', 1), ('right', 2)]),
        (True, '', '', {"keep": "yes"}),
        (False, '', '', {"keep": "yes"}),
    ],
)
async def test_login_redirect(app, browser, running, next_url, location, params, user):

    if location:
        location = ujoin(app.base_url, location)
        print("if location is:" + location)
    elif running:
        # location not specified,
        location = user.url
        if params:
            location = url_concat(location, params)
    else:
        # use default url
        location = ujoin(app.base_url, 'hub/spawn')
        if params:
            location = url_concat(location, params)

    url = 'login'
    if params:
        url = url_concat(url, params)
    if next_url:
        if next_url.startswith('/') and not (
            next_url.startswith("//") or urlparse(next_url).netloc
        ):
            next_url = ujoin(app.base_url, next_url, '')
        url = url_concat(url, dict(next=next_url))

    if running and not user.active:
        # ensure running
        await user.spawn()
    elif user.active and not running:
        # ensure not running
        await user.stop()
    time.sleep(5)
    # open_url(app,browser)
    await in_thread(browser.get, (ujoin(public_url(app), url)))
    await login(browser, user='test_user', pass_w='test_user')

    # await get_page(url, app, allow_redirects=False)
    time.sleep(50)

    if user != 'admin' and next_url == '/hub/admin':  # user!=user.admin
        assert browser.current_url.endswith('hub/admin/')
        elm = browser.find_element(
            LoginPageLocators.ERROR_403
        )  # .get_attribute('action')
        print(elm)
        assert elm == LoginPageLocators.ERROR_MESSAGES_403
        if params:
            assert browser.current_url.endswith('hub/admin/')
            elm = browser.find_element(
                *LoginPageLocators.ERROR_403
            )  # .get_attribute('action')
            print(elm)
            assert elm == LoginPageLocators.ERROR_MESSAGES_403

    elif next_url == '/has?repo=https':
        # print(app.users['test_user'].keys())
        print("else if")
    else:
        print("else")

    """
    <div class="error">


</div>
    0. 1., 9-14, 17-18 /space word/user/test_user/
    1. /space word/user/test_user/
    2. - 15,16 - space word/hub/admin  <h1>
    403 : Forbidden
  </h1>: <h1>
    <p>
    Action is not authorized with current scopes; requires any of [admin-ui]
  </p>

    3. space word/hub/user/other   <h1>
    404 : Not Found
  </h1> <p>Jupyter has lots of moons, but this is not one...</p>
    4. - 8.  the same as 3
    """

    """
    print("url ---" +browser.current_url)

    #print("user ()" +f"{user}")
    print("user (type)" +str(user))
    assert location in browser.current_url      """


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
    time.sleep(5)
    error = browser.find_element(*LoginPageLocators.ERROR_INVALID_CREDANTIALS).text

    # verify error message and url
    assert LoginPageLocators.ERROR_MESSAGES_LOGIN == error
    assert 'hub/login' in browser.current_url

    """"on page http://localhost:8000/user/username/lab
    check only page title for now"""


async def test_logout(app, browser):
    if is_displayed(browser, HomePageLocators.BUTTON_LOGOUT) == True:
        click(browser, HomePageLocators.BUTTON_LOGOUT)
    else:
        print("TBD")
    await async_requests.get(public_host(app))

    assert 'hub/login' in browser.current_url


# HOME PAGE


def navigate_bar():
    print("TBD")


# TOKEN PAGE
@pytest.mark.parametrize(
    "user, pass_w",
    [
        ("user", "user"),
    ],
)
async def test_elements_of_token_page(app, browser, user, pass_w):
    await open_url(app, browser)
    await login(browser, user, pass_w)

    cookies = await app.login_user(user)
    await get_page("token", app, cookies=cookies)
    # await get_page("token", app)

    buttonAPI = is_displayed(browser, TokenPageLocators.BUTTON_API_REQ)
    token_note = is_displayed(browser, TokenPageLocators.INPUT_TOKEN)
    token_dropdown = is_displayed(browser, TokenPageLocators.LIST_EXP_TOKEN_FIELD)

    options = browser.find_elements(TokenPageLocators.LIST_EXP_TOKEN_OPT)
    for option in options:
        is_selected = option.is_selected()
    print(str(is_selected))

    """TBD"""
    assert buttonAPI == True
    assert token_note == True
    assert token_dropdown == True
    assert str(is_selected) == "Never"


async def test_request_token(app, browser, user, pass_w):
    await login(app, browser, user, pass_w)
    cookies = await app.login_user(user)
    await get_page("token", app, cookies=cookies)
