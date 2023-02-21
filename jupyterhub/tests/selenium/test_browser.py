"""Tests for the Selenium WebDriver"""

import asyncio
import json
from functools import partial

import pytest
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from tornado.escape import url_escape
from tornado.httputil import url_concat

from jupyterhub import scopes
from jupyterhub.tests.selenium.locators import (
    BarLocators,
    HomePageLocators,
    LoginPageLocators,
    SpawningPageLocators,
    TokenPageLocators,
)
from jupyterhub.utils import exponential_backoff

from ... import orm, roles
from ...utils import url_path_join
from ..utils import api_request, public_host, public_url, ujoin

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


async def open_url(app, browser, path):
    """initiate to open the hub page in the browser"""

    url = url_path_join(public_host(app), app.hub.base_url, path)
    await in_thread(browser.get, url)
    return url


async def click(browser, by_locator):
    """wait for element to be visible, then click on it"""
    el = WebDriverWait(browser, 10).until(EC.visibility_of_element_located(by_locator))

    await in_thread(el.click)


def is_displayed(browser, by_locator):
    """Whether the element is visible or not"""

    try:
        return (
            WebDriverWait(browser, 10)
            .until(EC.visibility_of_element_located(by_locator))
            .is_displayed()
        )
    except:
        return False


def send_text(browser, by_locator, text):
    """wait for element to be presented, then put the text in it"""

    return (
        WebDriverWait(browser, 10)
        .until(EC.presence_of_element_located(by_locator))
        .send_keys(text)
    )


# LOGIN PAGE


async def login(browser, username, pass_w):
    """filling the login form by user and pass_w parameters and iniate the login"""

    # fill in username field
    send_text(browser, LoginPageLocators.ACCOUNT, username)
    # fill in password field
    send_text(browser, LoginPageLocators.PASSWORD, pass_w)
    # click submit button
    current_url = browser.current_url
    await click(browser, (By.ID, "login_submit"))
    await webdriver_wait(browser, EC.url_changes(current_url))


async def test_submit_login_form(app, browser, user):
    await open_url(app, browser, path="login")
    redirected_url = ujoin(public_url(app), f"/user/{user.name}/")
    await login(browser, user.name, pass_w=str(user.name))
    # verify url contains username
    if f"/user/{user.name}/" not in browser.current_url:
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
    user,
):
    await open_url(app, browser, path=url)
    url_new = url_path_join(public_host(app), app.hub.base_url, url_concat(url, params))
    await in_thread(browser.get, url_new)
    redirected_url = redirected_url.replace('{{BASE_URL}}', url_escape(app.base_url))
    form_action = form_action.replace('{{BASE_URL}}', url_escape(app.base_url))
    form = browser.find_element(*LoginPageLocators.FORM_LOGIN).get_attribute('action')

    # verify title / url
    assert browser.title == 'JupyterHub'
    assert form.endswith(form_action)
    # login in with params
    await login(browser, user.name, pass_w=str(user.name))
    # verify next url + params
    next_url = browser.current_url
    if url_escape(app.base_url) in form_action:
        assert next_url.endswith("param=value")
    elif "next=%2Fhub" in form_action:
        assert next_url.endswith("spawn?param=value")
        assert f"user/{user.name}/" not in next_url
    else:
        if not next_url.endswith(f"/user/{user.name}/"):
            await webdriver_wait(
                browser, EC.url_to_be(ujoin(public_url(app), f"/user/{user.name}/"))
            )
            next_url = browser.current_url
        assert next_url.endswith(f"/user/{user.name}/")


@pytest.mark.parametrize(
    "username, pass_w",
    [
        (" ", ""),
        ("user", ""),
        (" ", "password"),
        ("user", "password"),
    ],
)
async def test_login_with_invalid_credantials(app, browser, username, pass_w):
    await open_url(app, browser, path="login")
    await login(browser, username, pass_w)
    while not is_displayed(browser, LoginPageLocators.ERROR_INVALID_CREDANTIALS):
        try:
            await webdriver_wait(
                browser,
                EC.visibility_of_element_located(
                    LoginPageLocators.ERROR_INVALID_CREDANTIALS
                ),
            )
        except NoSuchElementException:
            break
    element_error_message = browser.find_element(
        *LoginPageLocators.ERROR_INVALID_CREDANTIALS
    )
    # verify error message and url
    expected_error_message = "Invalid username or password"
    assert element_error_message.text == expected_error_message
    # make sure we're still on the login page
    assert 'hub/login' in browser.current_url


# SPAWNING


async def open_spawn_pending(app, browser, user):
    url = url_path_join(
        public_host(app),
        url_concat(
            url_path_join(app.base_url, "login"),
            {"next": url_path_join(app.base_url, "hub/home")},
        ),
    )
    await in_thread(browser.get, url)
    await login(browser, user.name, pass_w=str(user.name))
    url_spawn = url_path_join(
        public_host(app), app.hub.base_url, '/spawn-pending/' + user.name
    )
    await in_thread(browser.get, url_spawn)
    await webdriver_wait(browser, EC.url_to_be(url_spawn))
    # wait for javascript to finish loading
    await wait_for_ready(browser)


async def test_spawn_pending_server_not_started(
    app, browser, slow_spawn, no_patience, user
):
    # first request, no spawn is pending
    # spawn-pending shows button linking to spawn
    await open_spawn_pending(app, browser, user)
    # on the page verify the button and expected information
    assert is_displayed(browser, (By.ID, "start"))

    buttons_stop_start = browser.find_elements(*SpawningPageLocators.BUTTONS_SERVER)
    # verify that only one button is displayed  - the start button
    assert len(buttons_stop_start) == 1
    for button in buttons_stop_start:
        id = button.get_attribute('id')
        href_launch = button.get_attribute('href')
        name_button = button.text
    assert id == "start"
    expected_button_name = "Launch Server"
    assert name_button == expected_button_name
    assert href_launch.endswith(f"/hub/spawn/{user.name}")
    # verify that texts which say the server is not started yet displayed
    titles_on_page = browser.find_elements(*SpawningPageLocators.TEXT_SERVER_TITLE)
    assert len(titles_on_page) == 1
    for title_on_page in titles_on_page:
        title_on_page.text
    assert title_on_page.text == SpawningPageLocators.TEXT_SERVER_NOT_RUN_YET

    texts_on_page = browser.find_elements(*SpawningPageLocators.TEXT_SERVER)
    assert len(texts_on_page) == 1
    for text_on_page in texts_on_page:
        text_on_page.text
    assert text_on_page.text == SpawningPageLocators.TEXT_SERVER_NOT_RUNNING


# this test is flaky on CI, but runs reliably locally
@pytest.mark.xfail(reason="flaky on CI")
async def test_spawn_pending_progress(app, browser, slow_spawn, no_patience, user):
    """verify that the server process messages are showing up to the user
    when the server is going to start up"""
    # begin starting the server
    await api_request(app, f"/users/{user.name}/server", method="post")
    # visit the spawn-pending page
    await open_spawn_pending(app, browser, user)
    assert '/spawn-pending/' in browser.current_url

    # wait for progress _or_ url change
    # so we aren't waiting forever if the next page is already loaded
    def wait_for_progress(browser):
        vis = EC.visibility_of_element_located((By.CLASS_NAME, "progress-bar"))(
            browser
        ).is_displayed()
        return vis or '/spawn-pending/' not in browser.current_url

    await webdriver_wait(browser, wait_for_progress)
    # make sure we're still on the spawn-pending page
    assert '/spawn-pending/' in browser.current_url
    while '/spawn-pending/' in browser.current_url:
        # FIXME: reliability may be due to page changing between `find_element` calls
        # maybe better if we get HTML once and parse with beautifulsoup
        progress_message = browser.find_element(By.ID, "progress-message").text
        # checking text messages that the server is starting to up
        texts = browser.find_elements(*SpawningPageLocators.TEXT_SERVER)
        texts_list = []
        for text in texts:
            text.text
            texts_list.append(text.text)
        assert str(texts_list[0]) == SpawningPageLocators.TEXT_SERVER_STARTING
        assert str(texts_list[1]) == SpawningPageLocators.TEXT_SERVER_REDIRECT
        # checking progress of the servers starting (messages, % progress and events log))
        logs_list = []
        try:
            progress_bar = browser.find_element(By.CLASS_NAME, "progress-bar")
            progress = browser.find_element(By.ID, "progress-message")
            logs = browser.find_elements(By.CLASS_NAME, "progress-log-event")
            percent = (
                progress_bar.get_attribute('style').split(';')[0].split(':')[1].strip()
            )
            for log in logs:
                # only include non-empty log messages
                # avoid partially-created elements
                if log.text:
                    logs_list.append(log.text)
        except (NoSuchElementException, StaleElementReferenceException):
            break

        expected_messages = [
            "Server requested",
            "Spawning server...",
            f"Server ready at {app.base_url}user/{user.name}/",
        ]

        if progress_message:
            assert progress_message in expected_messages
        if logs_list:
            # race condition: progress_message _should_
            # be the last log message, but it _may_ be the next one
            assert progress_message

        if len(logs_list) < 2:
            assert percent == "0%"
        elif len(logs_list) == 2:
            assert percent == "50%"
        elif len(logs_list) >= 3:
            assert percent == "100%"

        assert logs_list == expected_messages[: len(logs_list)]

        # Wait for the server button to disappear and progress bar to show (2sec is too much)
        await asyncio.sleep(0.2)

    # after spawn-pending redirect
    assert f'/user/{user.name}' in browser.current_url


async def test_spawn_pending_server_ready(app, browser, user):
    """verify that after a successful launch server via the spawn-pending page
    the user should see two buttons on the home page"""

    await open_spawn_pending(app, browser, user)
    button_start = browser.find_element(By.ID, "start")
    await click(browser, (By.ID, "start"))
    await webdriver_wait(browser, EC.staleness_of(button_start))
    # checking that server is running and two butons present on the home page
    home_page = url_path_join(public_host(app), ujoin(app.base_url, "hub/home"))
    while not user.spawner.ready:
        await asyncio.sleep(0.01)
    await in_thread(browser.get, home_page)
    await wait_for_ready(browser)
    assert is_displayed(browser, (By.ID, "stop"))
    assert is_displayed(browser, (By.ID, "start"))


# HOME PAGE


async def wait_for_ready(browser):
    """Wait for javascript on the page to finish loading

    otherwise, click events may not do anything
    """
    await webdriver_wait(
        browser,
        lambda driver: driver.execute_script("return window._jupyterhub_page_loaded;"),
    )


async def open_home_page(app, browser, user):
    """function to open the home page"""

    home_page = url_escape(app.base_url) + "hub/home"
    await open_url(app, browser, path="/login?next=" + home_page)
    await login(browser, user.name, pass_w=str(user.name))
    await webdriver_wait(browser, EC.url_contains('/hub/home'))
    # wait for javascript to finish loading
    await wait_for_ready(browser)


async def test_start_button_server_not_started(app, browser, user):
    """verify that when server is not started one button is availeble,
    after starting 2 buttons are available"""
    await open_home_page(app, browser, user)
    # checking that only one button is presented
    assert is_displayed(browser, (By.ID, "start"))
    buttons_stop_start = browser.find_elements(*HomePageLocators.BUTTONS_SERVER)
    assert len(buttons_stop_start) == 1
    # checking link and name of the start button when server is going to be started
    for button in buttons_stop_start:
        id = button.get_attribute('id')
        href_start = button.get_attribute('href')
        name_button = button.text
    assert id == "start"
    expected_button_name = "Start My Server"
    assert name_button == expected_button_name
    assert href_start.endswith(f"/hub/spawn/{user.name}")

    # Start server via clicking on the Start button
    await click(browser, (By.ID, "start"))
    next_url = url_path_join(public_host(app), app.base_url, '/hub/home')
    await in_thread(browser.get, next_url)
    # wait for javascript to finish loading
    await wait_for_ready(browser)
    assert is_displayed(browser, (By.ID, "start"))
    assert is_displayed(browser, (By.ID, "stop"))
    # verify that 2 buttons are displayed on the home page
    buttons_stop_start = browser.find_elements(*HomePageLocators.BUTTONS_SERVER)
    if len(buttons_stop_start) != 2:
        await webdriver_wait(
            browser, EC.visibility_of_all_elements_located(buttons_stop_start)
        )
    for button in buttons_stop_start:
        id = button.get_attribute('id')
        href = button.get_attribute('href')
        style = button.get_attribute('style')
        assert not style
    # verify attributes of buttons
    assert buttons_stop_start[0].get_attribute('id') == "stop"
    assert buttons_stop_start[0].get_attribute('href') == None
    assert buttons_stop_start[1].get_attribute('id') == "start"
    assert buttons_stop_start[1].get_attribute('href').endswith(f"/user/{user.name}")

    expected_stop_button_name = "Stop My Server"
    expected_start_button_name = "My Server"
    assert buttons_stop_start[0].text == expected_stop_button_name
    assert buttons_stop_start[1].text == expected_start_button_name


async def test_stop_button(app, browser, user):
    """verify that the stop button after stoping a server is not shown
    the start button is displayed with new name"""

    await open_home_page(app, browser, user)
    if is_displayed(browser, (By.ID, "start")):
        await click(browser, (By.ID, "start"))
    next_url = url_path_join(public_host(app), app.base_url, '/hub/home')
    await in_thread(browser.get, next_url)
    # wait for javascript to finish loading
    await wait_for_ready(browser)
    buttons_stop_start = browser.find_elements(*HomePageLocators.BUTTONS_SERVER)
    if len(buttons_stop_start) != 2:
        await webdriver_wait(
            browser, EC.visibility_of_all_elements_located(buttons_stop_start)
        )
    while not user.spawner.ready:
        # added this stop click event is registered in JS to verify that the process is not still pending
        await asyncio.sleep(0.1)
    # Stop server via clicking on the Stop button
    await click(browser, (By.ID, "stop"))
    # verify that the stop button is invisible on the page
    await webdriver_wait(browser, EC.invisibility_of_element_located((By.ID, "stop")))
    buttons_stop_start = browser.find_elements(*HomePageLocators.BUTTONS_SERVER)
    assert len(buttons_stop_start) == 2
    # checking attributes of buttons after server was stopped
    for button in buttons_stop_start:
        id = button.get_attribute('id')
        href = button.get_attribute('href')
        style = button.get_attribute('style')
    assert buttons_stop_start[0].get_attribute('id') == "stop"
    assert buttons_stop_start[0].get_attribute('style') == "display: none;"
    assert buttons_stop_start[0].get_attribute('href') == None
    assert buttons_stop_start[1].get_attribute('id') == "start"
    assert (
        buttons_stop_start[1].get_attribute('href').endswith(f"/hub/spawn/{user.name}")
    )
    expected_start_button_name = "Start My Server"
    assert buttons_stop_start[1].text == expected_start_button_name


# TOKEN PAGE


async def open_token_page(app, browser, user):
    """function to open the token page"""

    token_page = url_escape(app.base_url) + "hub/token"
    await open_url(app, browser, path="/login?next=" + token_page)
    await login(browser, user.name, pass_w=str(user.name))
    await webdriver_wait(browser, EC.url_contains('/hub/token'))
    # wait for javascript to finish loading
    await wait_for_ready(browser)
    # wait for moment.js to format
    await asyncio.sleep(0.1)


def token_table_body_as_dict(browser, table_locator):
    # get the token table elements (excluding of the tables header)
    table = browser.find_element(*table_locator)
    body = table.find_element(By.TAG_NAME, 'tbody')
    row = body.find_elements(By.CLASS_NAME, 'token-row')
    # return dict contains elements in row and column
    return [
        [element.text for element in row.find_elements(By.TAG_NAME, 'td')]
        for row in body.find_elements(By.TAG_NAME, 'tr')
    ]


async def test_token_request_form_and_panel(app, browser, user):
    """verify elements of the request token form"""
    await open_token_page(app, browser, user)
    assert is_displayed(browser, TokenPageLocators.BUTTON_API_REQ)
    element_button_api_req = browser.find_element(*TokenPageLocators.BUTTON_API_REQ)
    button_api_req_name = element_button_api_req.get_attribute('innerHTML').strip()
    expected_button_name = 'Request new API token'
    assert button_api_req_name == expected_button_name
    assert is_displayed(browser, TokenPageLocators.LIST_EXP_TOKEN_FIELD)
    # checking that token expiration = "Never" selected by default
    select_element = browser.find_element(*TokenPageLocators.LIST_EXP_TOKEN_FIELD)
    select = Select(select_element)
    newer_element = browser.find_element(*TokenPageLocators.NEVER_EXP)
    option_elements = select_element.find_elements(By.TAG_NAME, 'option')
    option_list = select.options
    selected_option_list = select.all_selected_options
    expected_selection = [newer_element]
    assert option_elements == option_list
    assert selected_option_list == expected_selection
    assert newer_element.text == "Never"
    assert newer_element.is_selected()
    # verify that dropdown list contains expected items
    dict_opt_list = {}
    for option in option_elements:
        dict_opt_list[option.text] = option.get_attribute('value')
    assert dict_opt_list == TokenPageLocators.LIST_EXP_TOKEN_OPT_DICT
    # verify that field for input notes is empty by default
    assert browser.find_element(By.ID, "token-note").get_attribute('value') == ""
    await click(browser, TokenPageLocators.BUTTON_API_REQ)
    await webdriver_wait(
        browser, EC.visibility_of_element_located((By.ID, 'token-area'))
    )
    # verify that "Your new API Token" panel shows up with the new API token
    assert is_displayed(browser, (By.ID, 'token-area'))
    assert not browser.find_element(By.ID, 'token-area').get_attribute('style')
    element_panel_token = browser.find_element(By.CLASS_NAME, 'panel-heading')
    expected_panel_token_title = "Your new API Token"
    assert element_panel_token.text == expected_panel_token_title
    element_token = browser.find_element(By.ID, 'token-result')
    assert element_token
    # refresh the page
    await in_thread(browser.get, browser.current_url)
    # verify that "Your new API Token" panel is hidden after refresh the page
    await webdriver_wait(
        browser, EC.invisibility_of_element_located((By.ID, 'token-area'))
    )
    assert (
        browser.find_element(By.ID, 'token-area').get_attribute('style')
        == "display: none;"
    )
    element_api_token_table = browser.find_element(*TokenPageLocators.TOKEN_TABLE)
    assert element_api_token_table.is_displayed()


@pytest.mark.parametrize(
    "token_opt, note",
    [
        ("1 Hour", 'some note'),
        ("1 Day", False),
        ("1 Week", False),
        ("Never", 'some note'),
        # "server_up" token type is not from the list in the token request form:
        # when the server started it shows on the API Tokens table
        ("server_up", False),
    ],
)
async def test_request_token_expiration(app, browser, token_opt, note, user):
    """verify request token with the different options"""
    if token_opt == "server_up":
        # open the home page
        await open_home_page(app, browser, user)
        assert "/hub/home" in browser.current_url
        # Start server via clicking on the Start button
        await click(browser, (By.ID, "start"))
        while not user.spawner.ready:
            await asyncio.sleep(0.01)
        next_url = url_path_join(public_host(app), app.base_url, '/hub/token')
        await in_thread(browser.get, next_url)
    else:
        # open the token page
        await open_token_page(app, browser, user)
        assert is_displayed(browser, TokenPageLocators.LIST_EXP_TOKEN_FIELD)
        # select the token duration
        select_element = browser.find_element(*TokenPageLocators.LIST_EXP_TOKEN_FIELD)
        element_token_note = browser.find_element(By.ID, "token-note")
        while token_opt != ("Never" and "server_up"):
            select = Select(select_element)
            select.select_by_visible_text(token_opt)
            break
        if note:
            send_text(browser, (By.ID, "token-note"), note)
            assert element_token_note.get_attribute('value') == note
        else:
            assert element_token_note.get_attribute('value') == ""
        await click(browser, TokenPageLocators.BUTTON_API_REQ)
        await webdriver_wait(
            browser, EC.visibility_of_element_located((By.ID, 'token-area'))
        )
        # getting the token_id
        token = browser.find_element(By.ID, 'token-result').text
        # refresh the page
        await in_thread(browser.get, browser.current_url)
        # wait for javascript, moment.js to format
        await wait_for_ready(browser)
    # API Tokens table: verify that elements are displayed
    assert is_displayed(browser, TokenPageLocators.TOKEN_TABLE)
    assert is_displayed(browser, TokenPageLocators.TOKEN_TABLE_HEADER)
    assert len(token_table_body_as_dict(browser, TokenPageLocators.TOKEN_TABLE)) == 1

    # getting values from DB to compare with values on UI
    assert len(user.api_tokens) == 1
    orm_token = user.api_tokens[-1]

    if token_opt == "server_up":
        expected_note = "Server at " + ujoin(app.base_url, f"/user/{user.name}/")
    elif note:
        expected_note = note
    else:
        expected_note = "Requested via token page"

    assert orm_token.note == expected_note
    note_on_page = token_table_body_as_dict(browser, TokenPageLocators.TOKEN_TABLE)[0][
        0
    ]
    assert note_on_page == expected_note

    expires_at_text = token_table_body_as_dict(browser, TokenPageLocators.TOKEN_TABLE)[
        0
    ][3]
    last_used_text = token_table_body_as_dict(browser, TokenPageLocators.TOKEN_TABLE)[
        0
    ][1]
    assert last_used_text == "Never"

    if token_opt == "Never":
        assert orm_token.expires_at is None
        assert expires_at_text == "Never"
    elif token_opt == "1 Hour":
        assert expires_at_text == "in an hour"
    elif token_opt == "1 Day":
        assert expires_at_text == "in a day"
    elif token_opt == "1 Week":
        assert expires_at_text == "in 7 days"
    elif token_opt == "server_up":
        assert orm_token.expires_at is None
        assert expires_at_text == "Never"

    # verify that the button for revoke is presented
    revoke_button = browser.find_elements(*TokenPageLocators.BUTTON_REVOKE_TOKEN)[0]
    assert revoke_button.text == "revoke"


@pytest.mark.parametrize(
    "token_type",
    [
        ("server_up"),
        ("request_by_user"),
        ("both"),
    ],
)
async def test_revoke_token(app, browser, token_type, user):
    """verify API Tokens table contant in case the server is started"""

    # open the home page
    await open_home_page(app, browser, user)
    if token_type == "server_up" or token_type == "both":
        assert "/hub/home" in browser.current_url
        # Start server via clicking on the Start button
        await click(browser, (By.ID, "start"))
        while not user.spawner.ready:
            await asyncio.sleep(0.01)
    # open the token page
    next_url = url_path_join(public_host(app), app.base_url, '/hub/token')
    await in_thread(browser.get, next_url)
    assert next_url in browser.current_url
    if token_type == "both" or token_type == "request_by_user":
        await asyncio.sleep(0.1)
        await click(browser, TokenPageLocators.BUTTON_API_REQ)
        await webdriver_wait(
            browser, EC.visibility_of_element_located((By.ID, 'token-area'))
        )
        # refresh the page
        await in_thread(browser.get, browser.current_url)
    # wait for javascript
    await wait_for_ready(browser)
    revoke_buttons = browser.find_elements(*TokenPageLocators.BUTTON_REVOKE_TOKEN)
    await webdriver_wait(
        browser,
        EC.visibility_of_all_elements_located(TokenPageLocators.BUTTON_REVOKE_TOKEN),
    )
    # verify that the token revoked from UI and the database
    if token_type in {"server_up", "request_by_user"}:
        assert len(revoke_buttons) == 1
        assert len(user.api_tokens) == 1
        await click(browser, TokenPageLocators.BUTTON_REVOKE_TOKEN)
        await webdriver_wait(
            browser,
            EC.none_of(
                EC.presence_of_all_elements_located(
                    TokenPageLocators.TOKEN_TABLE_ROWS_BY_CLASS
                )
            ),
        )
        revoke_buttons = browser.find_elements(*TokenPageLocators.BUTTON_REVOKE_TOKEN)
        assert (
            len(token_table_body_as_dict(browser, TokenPageLocators.TOKEN_TABLE)) == 0
        )
        assert len(revoke_buttons) == 0
        assert len(user.api_tokens) == 0
    if token_type == "both":
        # verify that both tokens are revoked from UI and the database
        assert len(revoke_buttons) == 2
        assert len(user.api_tokens) == 2
        while len(revoke_buttons) != 0:
            await click(browser, TokenPageLocators.BUTTON_REVOKE_TOKEN)
            # wait for the row with revoked token disappears
            revoke_buttons = browser.find_elements(
                *TokenPageLocators.BUTTON_REVOKE_TOKEN
            )
            assert len(revoke_buttons) == len(
                token_table_body_as_dict(browser, TokenPageLocators.TOKEN_TABLE)
            )
        assert len(revoke_buttons) == 0
        assert len(user.api_tokens) == 0


# MENU BAR


@pytest.mark.parametrize(
    "page, logged_in",
    [
        # the home page: verify if links work on the top bar
        ("/hub/home", True),
        # the token page: verify if links work on the top bar
        ("/hub/token", True),
        # "hub/not" = any url that is not existed: verify if links work on the top bar
        ("hub/not", True),
        # the login page: verify if links work on the top bar
        ("", False),
    ],
)
async def test_menu_bar(app, browser, page, logged_in, user):
    next_page = ujoin(url_escape(app.base_url) + page)
    await open_url(app, browser, path="/login?next=" + next_page)
    if page:
        await login(browser, user.name, pass_w=str(user.name))
    await webdriver_wait(
        browser, EC.presence_of_all_elements_located(BarLocators.LINK_HOME_BAR)
    )
    links_bar = browser.find_elements(*BarLocators.LINK_HOME_BAR)
    if not page:
        assert len(links_bar) == 1
    elif "hub/not" in page:
        assert len(links_bar) == 3
    else:
        assert len(links_bar) == 4
        user_name = browser.find_element(*BarLocators.USER_NAME)
        assert user_name.text == user.name
    # verify the title on the logo
    logo = browser.find_element(By.TAG_NAME, "img")
    assert logo.get_attribute('title') == "Home"
    for index in range(len(links_bar)):
        await webdriver_wait(
            browser, EC.presence_of_all_elements_located(BarLocators.LINK_HOME_BAR)
        )
        links_bar = browser.find_elements(*BarLocators.LINK_HOME_BAR)
        links_bar_url = links_bar[index].get_attribute('href')
        links_bar_title = links_bar[index].text
        await in_thread(links_bar[index].click)
        # verify that links on the topbar work, checking the titles of links
        expected_link_bar_url = ["/hub/", "/hub/home", "/hub/token", "/hub/logout"]
        expected_link_bar_name = ["", "Home", "Token", "Logout"]
        assert links_bar_title == expected_link_bar_name[index]
        assert links_bar_url.endswith(expected_link_bar_url[index])
        if index == 0:
            if not page:
                expected_url = f"hub/login?next={url_escape(app.base_url)}"
                assert expected_url in browser.current_url
            else:
                while not f"/user/{user.name}/" in browser.current_url:
                    await webdriver_wait(
                        browser, EC.url_contains(f"/user/{user.name}/")
                    )
                assert f"/user/{user.name}/" in browser.current_url
                browser.back()
                privious_page = ujoin(public_url(app), page)
                while not page in browser.current_url:
                    await webdriver_wait(browser, EC.url_to_be(privious_page))
                assert page in browser.current_url
        elif index > 0:
            if index != 3:
                assert expected_link_bar_url[index] in browser.current_url
            elif index == 3:
                assert "/login" in browser.current_url
            if page not in browser.current_url:
                browser.back()
            assert page in browser.current_url


# LOGOUT


@pytest.mark.parametrize(
    "url",
    [("/hub/home"), ("/hub/token"), ("/hub/spawn")],
)
async def test_user_logout(app, browser, url, user):
    if "/hub/home" in url:
        await open_home_page(app, browser, user)
    elif "/hub/token" in url:
        await open_home_page(app, browser, user)
    elif "/hub/spawn" in url:
        await open_spawn_pending(app, browser, user)
    await webdriver_wait(
        browser, EC.presence_of_all_elements_located(BarLocators.LINK_HOME_BAR)
    )
    await click(browser, (By.ID, "logout"))
    if 'hub/login' not in browser.current_url:
        await webdriver_wait(browser, EC.url_changes(browser.current_url))
    # checking url changing to login url and login form is displayed
    assert 'hub/login' in browser.current_url
    assert is_displayed(browser, LoginPageLocators.FORM_LOGIN)
    elements_home_bar = browser.find_elements(*BarLocators.LINK_HOME_BAR)
    assert len(elements_home_bar) == 1  # including 1 element
    for element_home_bar in elements_home_bar:
        assert element_home_bar.get_attribute('href').endswith('hub/')
    # verify that user can login after logout
    await login(browser, user.name, pass_w=str(user.name))
    while f"/user/{user.name}/" not in browser.current_url:
        await webdriver_wait(browser, EC.url_matches(f"/user/{user.name}/"))
    assert f"/user/{user.name}" in browser.current_url


# OAUTH confirmation page


@pytest.mark.parametrize(
    "user_scopes",
    [
        ([]),  # no scopes
        (  # user has just access to own resources
            [
                'self',
            ]
        ),
        (  # user has access to all groups resources
            [
                'read:groups',
                'groups',
            ]
        ),
        (  # user has access to specific users/groups/services resources
            [
                'read:users!user=gawain',
                'read:groups!group=mythos',
                'read:services!service=test',
            ]
        ),
    ],
)
async def test_oauth_page(
    app,
    browser,
    mockservice_url,
    create_temp_role,
    create_user_with_scopes,
    user_scopes,
):
    # create user with appropriate access permissions
    service_role = create_temp_role(user_scopes)
    service = mockservice_url
    user = create_user_with_scopes("access:services")
    roles.grant_role(app.db, user, service_role)
    oauth_client = (
        app.db.query(orm.OAuthClient)
        .filter_by(identifier=service.oauth_client_id)
        .one()
    )
    oauth_client.allowed_scopes = sorted(roles.roles_to_scopes([service_role]))
    app.db.commit()
    # open the service url in the browser
    service_url = url_path_join(public_url(app, service) + 'owhoami/?arg=x')
    await in_thread(browser.get, (service_url))
    expected_client_id = service.name
    expected_redirect_url = app.base_url + f"servises/{service.name}/oauth_callback"
    assert expected_client_id, expected_redirect_url in browser.current_url

    # login user
    await login(browser, user.name, pass_w=str(user.name))
    auth_button = browser.find_element(By.XPATH, '//input[@type="submit"]')
    if not auth_button.is_displayed():
        await webdriver_wait(
            browser,
            EC.visibility_of_element_located((By.XPATH, '//input[@type="submit"]')),
        )
    # verify that user can see the service name and oauth URL
    text_permission = browser.find_element(
        By.XPATH, './/h1[text()="Authorize access"]//following::p'
    ).text
    assert f"JupyterHub service {service.name}", (
        f"oauth URL: {expected_redirect_url}" in text_permission
    )
    # permissions check
    oauth_form = browser.find_element(By.TAG_NAME, "form")
    scopes_elements = oauth_form.find_elements(
        By.XPATH, '//input[@type="hidden" and @name="scopes"]'
    )
    scope_list_oauth_page = []
    for scopes_element in scopes_elements:
        # checking that scopes are invisible on the page
        assert not scopes_element.is_displayed()
        scope_value = scopes_element.get_attribute("value")
        scope_list_oauth_page.append(scope_value)

    # checking that all scopes granded to user are presented in POST form (scope_list)
    assert all(x in scope_list_oauth_page for x in user_scopes)
    assert f"access:services!service={service.name}" in scope_list_oauth_page

    check_boxes = oauth_form.find_elements(
        By.XPATH, '//input[@type="checkbox" and @name="raw-scopes"]'
    )
    for check_box in check_boxes:
        # checking that user cannot uncheck the checkbox
        assert not check_box.is_enabled()
        assert check_box.get_attribute("disabled")
        assert check_box.get_attribute("title") == "This authorization is required"

    # checking that appropriete descriptions are displayed depending of scopes
    descriptions = oauth_form.find_elements(By.TAG_NAME, 'span')
    desc_list_form = [description.text.strip() for description in descriptions]
    # getting descriptions from scopes.py to compare them with descriptions on UI
    scope_descriptions = scopes.describe_raw_scopes(
        user_scopes or ['(no_scope)'], user.name
    )
    desc_list_expected = []
    for scope_description in scope_descriptions:
        description = scope_description.get("description")
        text_filter = scope_description.get("filter")
        if text_filter:
            description = f"{description} Applies to {text_filter}."
        desc_list_expected.append(description)

    assert sorted(desc_list_form) == sorted(desc_list_expected)

    # click on the Authorize button
    await click(browser, (By.XPATH, '//input[@type="submit"]'))
    # check that user returned to service page
    assert browser.current_url == service_url

    # check the granted permissions by
    # getting the scopes from the service page,
    # which contains the JupyterHub user model
    text = browser.find_element(By.TAG_NAME, "body").text
    user_model = json.loads(text)
    authorized_scopes = user_model["scopes"]

    # resolve the expected expanded scopes
    # authorized for the service
    expected_scopes = scopes.expand_scopes(user_scopes, owner=user.orm_user)
    expected_scopes |= scopes.access_scopes(oauth_client)
    expected_scopes |= scopes.identify_scopes(user.orm_user)

    # compare the scopes on the service page with the expected scope list
    assert sorted(authorized_scopes) == sorted(expected_scopes)


# ADMIN UI


async def open_admin_page(app, browser, login_as=None):
    """Login as `user` and open the admin page"""

    admin_page = url_escape(app.base_url) + "hub/admin"
    if login_as:
        user = login_as
        await open_url(app, browser, path="/login?next=" + admin_page)
        await login(browser, user.name, pass_w=str(user.name))
    else:
        await open_url(app, browser, admin_page)
    # waiting for loading of admin page elements
    await webdriver_wait(
        browser,
        lambda browser: is_displayed(
            browser, (By.XPATH, '//div[@class="resets"]/div[@data-testid="container"]')
        ),
    )


def create_list_of_users(create_user_with_scopes, n):
    return [create_user_with_scopes(["users"]) for i in range(1, n)]


async def test_open_admin_page(app, browser, admin_user):
    await open_admin_page(app, browser, admin_user)
    assert '/hub/admin' in browser.current_url


def get_users_buttons(browser, class_name):
    """returns the list of buttons in the user row(s) that match this class name"""

    all_btns = browser.find_elements(
        By.XPATH,
        f'//*[@data-testid="user-row-server-activity"]//button[contains(@class,"{class_name}")]',
    )
    return all_btns


async def click_and_wait_paging_btn(browser, buttons_number):
    """interecrion with paging buttons, where number 1 = previous and number 2 = next"""
    # number 1 - previous button, number 2 - next button
    await click(
        browser,
        (
            By.XPATH,
            f'//*[@class="pagination-footer"]//button[contains(@class, "btn-light")][{buttons_number}]',
        ),
    )


async def test_start_stop_all_servers_on_admin_page(app, browser, admin_user):
    await open_admin_page(app, browser, admin_user)
    # get total count of users from db
    users_count_db = app.db.query(orm.User).count()

    start_all_btn = browser.find_element(
        By.XPATH, '//button[@type="button" and @data-testid="start-all"]'
    )
    stop_all_btn = browser.find_element(
        By.XPATH, '//button[@type="button" and @data-testid="stop-all"]'
    )

    # verify Start All and Stop All buttons are displayed
    assert start_all_btn.is_displayed() and stop_all_btn.is_displayed()

    async def click_all_btns(browser, btn_type, btn_await):
        await click(
            browser,
            (By.XPATH, f'//button[@type="button" and @data-testid="{btn_type}"]'),
        )
        await webdriver_wait(
            browser,
            EC.visibility_of_all_elements_located(
                (
                    By.XPATH,
                    '//*[@data-testid="user-row-server-activity"]//button[contains(@class, "%s")]'
                    % str(btn_await),
                )
            ),
        )

    users = browser.find_elements(By.XPATH, '//td[@data-testid="user-row-name"]')
    # verify that all servers are not started
    # users´numbers are the same as numbers of the start button and the Spawn page button
    # no Stop server buttons are displayed
    # no access buttons are displayed

    class_names = ["stop-button", "primary", "start-button", "secondary"]
    btns = {
        class_name: get_users_buttons(browser, class_name) for class_name in class_names
    }
    print(btns)
    assert (
        len(btns["start-button"])
        == len(btns["secondary"])
        == len(users)
        == users_count_db
    )
    assert not btns["stop-button"] and not btns["primary"]

    # start all servers via the Start All
    await click_all_btns(browser, "start-all", "stop-button")
    # Start All and Stop All are still displayed
    assert start_all_btn.is_displayed() and stop_all_btn.is_displayed()

    # users´numbers are the same as numbers of the stop button and the Access button
    # no Start server buttons are displayed
    # no Spawn page buttons are displayed
    btns = {
        class_name: get_users_buttons(browser, class_name) for class_name in class_names
    }
    assert (
        len(btns["stop-button"]) == len(btns["primary"]) == len(users) == users_count_db
    )
    assert not btns["start-button"] and not btns["secondary"]

    # stop all servers via the Stop All
    await click_all_btns(browser, "stop-all", "start-button")

    # verify that all servers are stopped
    # users´numbers are the same as numbers of the start button and the Spawn page button
    # no Stop server buttons are displayed
    # no access buttons are displayed
    assert start_all_btn.is_displayed() and stop_all_btn.is_displayed()
    btns = {
        class_name: get_users_buttons(browser, class_name) for class_name in class_names
    }
    assert (
        len(btns["start-button"])
        == len(btns["secondary"])
        == len(users)
        == users_count_db
    )
    assert not btns["stop-button"] and not btns["primary"]


@pytest.mark.parametrize("added_count_users", [10, 47, 48, 49, 110])
async def test_paging_on_admin_page(
    app, browser, admin_user, added_count_users, create_user_with_scopes
):
    create_list_of_users(create_user_with_scopes, added_count_users)
    await open_admin_page(app, browser, admin_user)
    users = browser.find_elements(By.XPATH, '//td[@data-testid="user-row-name"]')

    # get total count of users from db
    users_count_db = app.db.query(orm.User).count()
    # get total count of users from UI page
    users_list = [user.text for user in users]
    displaying = browser.find_element(
        By.XPATH, '//*[@class="pagination-footer"]//*[contains(text(),"Displaying")]'
    )
    btn_previous = browser.find_element(
        By.XPATH, '//*[@class="pagination-footer"]//span[contains(text(),"Previous")]'
    )
    btn_next = browser.find_element(
        By.XPATH, '//*[@class="pagination-footer"]//span[contains(text(),"Next")]'
    )
    assert f"0-{min(users_count_db,50)}" in displaying.text
    if users_count_db > 50:
        assert btn_next.get_dom_attribute("class") == "active-pagination"
        # click on Next button
        await click_and_wait_paging_btn(browser, buttons_number=2)
        if users_count_db <= 100:
            assert f"50-{users_count_db}" in displaying.text
        else:
            assert "50-100" in displaying.text
            assert btn_next.get_dom_attribute("class") == "active-pagination"
        assert btn_previous.get_dom_attribute("class") == "active-pagination"
        # click on Previous button
        await click_and_wait_paging_btn(browser, buttons_number=1)
    else:
        assert btn_previous.get_dom_attribute("class") == "inactive-pagination"
        assert btn_next.get_dom_attribute("class") == "inactive-pagination"


@pytest.mark.parametrize(
    "added_count_users, search_value",
    [
        # the value of search is absent =>the expected result null records are found
        (10, "not exists"),
        # a search value is a middle part of users name (number,symbol,letter)
        (25, "r_5"),
        # a search value equals to number
        (50, "1"),
        # searching result shows on more than one page
        (60, "user"),
    ],
)
async def test_search_on_admin_page(
    app,
    browser,
    admin_user,
    create_user_with_scopes,
    added_count_users,
    search_value,
):
    create_list_of_users(create_user_with_scopes, added_count_users)
    await open_admin_page(app, browser, admin_user)
    element_search = browser.find_element(By.XPATH, '//input[@name="user_search"]')
    element_search.send_keys(search_value)
    await asyncio.sleep(1)
    # get the result of the search from db
    users_count_db_filtered = (
        app.db.query(orm.User).filter(orm.User.name.like(f'%{search_value}%')).count()
    )
    filtered_list_on_page = browser.find_elements(By.XPATH, '//*[@class="user-row"]')
    # check that count of users matches with number of users on the footer
    displaying = browser.find_element(
        By.XPATH, '//*[@class="pagination-footer"]//*[contains(text(),"Displaying")]'
    )
    # check that users names contain the search value in the filtered list
    for element in filtered_list_on_page:
        name = element.find_element(
            By.XPATH,
            '//*[@data-testid="user-row-name"]//span[contains(@data-testid, "user-name-div")]',
        )
        assert search_value in name.text
    if users_count_db_filtered <= 50:
        assert "0-" + str(users_count_db_filtered) in displaying.text
        assert len(filtered_list_on_page) == users_count_db_filtered
    else:
        assert "0-50" in displaying.text
        assert len(filtered_list_on_page) == 50
        # click on Next button to verify that the rest part of filtered list is displayed on the next page
        await click_and_wait_paging_btn(browser, buttons_number=2)
        filtered_list_on_next_page = browser.find_elements(
            By.XPATH, '//*[@class="user-row"]'
        )
        assert users_count_db_filtered - 50 == len(filtered_list_on_next_page)
        for element in filtered_list_on_next_page:
            name = element.find_element(
                By.XPATH,
                '//*[@data-testid="user-row-name"]//span[contains(@data-testid, "user-name-div")]',
            )
        assert search_value in name.text


@pytest.mark.parametrize(
    "added_count_users, index_user_1, index_user_2",
    [
        (5, 1, 0),
    ],
)
async def test_start_stop_server_on_admin_page(
    app,
    browser,
    admin_user,
    create_user_with_scopes,
    added_count_users,
    index_user_1,
    index_user_2,
):
    async def start_user(browser, expected_user):
        start_button_xpath = f'//a[contains(@href, "spawn/{expected_user[0]}")]/preceding-sibling::button[contains(@class, "start-button")]'
        await click(browser, (By.XPATH, start_button_xpath))
        start_btn = browser.find_element(By.XPATH, start_button_xpath)
        await wait_for_ready(browser)
        await webdriver_wait(browser, EC.staleness_of(start_btn))

    async def spawn_user(browser, app, expected_user):
        spawn_button_xpath = f'//a[contains(@href, "spawn/{expected_user[1]}")]/button[contains(@class, "secondary")]'
        await click(browser, (By.XPATH, spawn_button_xpath))
        while (
            not app.users[1].spawner.ready
            and f"/hub/spawn-pending/{expected_user[1]}" in browser.current_url
        ):
            await webdriver_wait(browser, EC.url_contains(f"/user/{expected_user[1]}/"))

    async def access_srv_user(browser, expected_user):
        access_buttons_xpath = '//*[@data-testid="user-row-server-activity"]//button[contains(@class, "primary")]'
        for i, ex_user in enumerate(expected_user):
            access_btn_xpath = f'//a[contains(@href, "user/{expected_user[i]}")]/button[contains(@class, "primary")]'
            await click(browser, (By.XPATH, access_btn_xpath))
            if not f"/user/{expected_user[i]}/" in browser.current_url:
                await webdriver_wait(
                    browser, EC.url_contains(f"/user/{expected_user[i]}/")
                )

    async def stop_srv_users(browser, expected_user):
        for i, ex_user in enumerate(expected_user):
            stop_btn_xpath = f'//a[contains(@href, "user/{expected_user[i]}")]/preceding-sibling::button[contains(@class, "stop-button")]'
            stop_btn = browser.find_element(By.XPATH, stop_btn_xpath)
            await click(browser, (By.XPATH, stop_btn_xpath))
            await webdriver_wait(browser, EC.staleness_of(stop_btn))

    create_list_of_users(create_user_with_scopes, added_count_users)
    await open_admin_page(app, browser, admin_user)
    users = browser.find_elements(By.XPATH, '//td[@data-testid="user-row-name"]')
    users_list = [user.text for user in users]

    expected_user = [users_list[index_user_1], users_list[index_user_2]]
    spawn_page_btns = browser.find_elements(
        By.XPATH,
        '//*[@data-testid="user-row-server-activity"]//a[contains(@href, "spawn/")]',
    )

    for i, user in enumerate(users):
        spawn_page_btn = spawn_page_btns[i]
        user_from_table = user.text
        link = spawn_page_btn.get_attribute('href')
    assert f"/spawn/{user_from_table}" in link

    # click on Start button
    await start_user(browser, expected_user)
    class_names = ["stop-button", "primary", "start-button", "secondary"]
    btns = {
        class_name: get_users_buttons(browser, class_name) for class_name in class_names
    }
    assert len(btns["stop-button"]) == 1

    # click on Spawn page button
    await spawn_user(browser, app, expected_user)
    assert f"/user/{expected_user[1]}/" in browser.current_url

    # open  the Admin page
    await open_url(app, browser, "/admin")
    # wait for javascript to finish loading
    await wait_for_ready(browser)
    assert "/hub/admin" in browser.current_url
    btns = {
        class_name: get_users_buttons(browser, class_name) for class_name in class_names
    }
    assert len(btns["stop-button"]) == len(btns["primary"]) == 2

    # click on the Access button
    await access_srv_user(browser, expected_user)

    # go back to the admin page
    await open_admin_page(app, browser)

    btns = {
        class_name: get_users_buttons(browser, class_name) for class_name in class_names
    }
    assert len(btns["stop-button"]) == 2

    # click on Stop button for both users
    await stop_srv_users(browser, expected_user)
    btns = {
        class_name: get_users_buttons(browser, class_name) for class_name in class_names
    }
    assert len(btns["stop-button"]) == 0
    assert len(btns["primary"]) == 0
