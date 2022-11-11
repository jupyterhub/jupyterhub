"""Tests for the Selenium WebDriver"""

import asyncio
import time
from functools import partial

import pytest
from pyparsing import empty
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from tornado.escape import url_escape
from tornado.httputil import url_concat

from jupyterhub.tests.selenium.locators import (
    BarLocators,
    HomePageLocators,
    LoginPageLocators,
    SpawningPageLocators,
    TokenPageLocators,
)
from jupyterhub.utils import exponential_backoff

from ... import orm
from ...utils import url_path_join
from ..utils import get_page, public_host, public_url, ujoin

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


async def open_url(app, browser, param):
    """initiate to open the hub page in the browser"""

    url = url_path_join(public_host(app), app.hub.base_url, param)
    await in_thread(browser.get, url)
    return url


def click(browser, by_locator):
    """wait for element to be visible, then click on it"""

    WebDriverWait(browser, 10).until(
        EC.visibility_of_element_located(by_locator)
    ).click()


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


def clear(browser, by_locator):
    """wait for element to be presented, then clear the text in it"""

    return (
        WebDriverWait(browser, 10)
        .until(EC.presence_of_element_located(by_locator))
        .clear()
    )


def elements_name(browser, by_locator, text):
    return WebDriverWait(browser, 10).until(
        EC.text_to_be_present_in_element(by_locator, text)
    )


# LOGIN PAGE


async def login(browser, user, pass_w):
    """filling the login form by user and pass_w parameters and iniate the login"""

    # fill in username field
    send_text(browser, LoginPageLocators.ACCOUNT, user)
    # fill in password field
    send_text(browser, LoginPageLocators.PASSWORD, pass_w)
    # click submit button
    click(browser, LoginPageLocators.LOGIN_BUTTON)
    await webdriver_wait(browser, EC.url_changes(browser.current_url))


async def test_submit_login_form(app, browser, user="test_user", pass_w="test_user"):

    await open_url(app, browser, param="login")
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

    await open_url(app, browser, param=url)
    url_new = url_path_join(public_host(app), app.hub.base_url, url_concat(url, params))
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
        u = app.users[orm.User.find(app.db, user)]
        while not u.spawner.ready:
            await webdriver_wait(browser, EC.url_changes(next_url))
        assert f"/{user}" in next_url
        assert f"/{params}" not in next_url


@pytest.mark.parametrize(
    "user, pass_w",
    [
        (" ", ""),
        ("user", ""),
        (" ", "password"),
        ("user", "password"),
    ],
)
async def test_login_with_invalid_credantials(app, browser, user, pass_w):
    await open_url(app, browser, param="login")
    await login(browser, user, pass_w)
    await asyncio.sleep(0.5)
    """adding for a catching of the reflected error"""
    try:
        error = browser.find_element(*LoginPageLocators.ERROR_INVALID_CREDANTIALS)
        await webdriver_wait(browser, EC.visibility_of(error))
    except NoSuchElementException:
        error = None

    # verify error message and url
    assert LoginPageLocators.ERROR_MESSAGES_LOGIN == error.text
    assert 'hub/login' in browser.current_url


# MENU BAR


@pytest.mark.parametrize(
    "value, user, pass_w",
    [
        # the home page: verify if links work on the top bar
        ("/hub/home", "test_user", "test_user"),
        # the token page: verify if links work on the top bar
        ("/hub/token", "test_user", "test_user"),
        # the spawn-pending page: verify if links work on the top bar
        ("hub/spawn", "test_user", "test_user"),
        # "hub/not" = any url that is not existed: verify if links work on the top bar
        ("hub/not", "test_user", "test_user"),
        # the login page: verify if links work on the top bar
        ("", None, None),
    ],
)
async def test_menu_bar(app, browser, slow_spawn, value, user, pass_w):
    next_page = ujoin(url_escape(app.base_url) + value)
    await open_url(app, browser, param="/login?next=" + next_page)
    if value:
        await login(browser, user, pass_w)
    await webdriver_wait(
        browser, EC.presence_of_all_elements_located(BarLocators.LINK_HOME_BAR)
    )
    logo = browser.find_element(*BarLocators.LOGO)
    # verify the title on the logo
    assert logo.get_attribute('title') == "Home"

    links_bar = browser.find_elements(*BarLocators.LINK_HOME_BAR)
    if not value:
        assert len(links_bar) == 1
    elif "hub/not" in value:
        assert len(links_bar) == 3
    else:
        assert len(links_bar) == 4
        user_name = browser.find_element(*BarLocators.USER_NAME)
        assert user_name.text == user

    for index in range(len(links_bar)):

        await webdriver_wait(
            browser, EC.presence_of_all_elements_located(BarLocators.LINK_HOME_BAR)
        )
        links_bar = browser.find_elements(*BarLocators.LINK_HOME_BAR)

        links_bar_url = links_bar[index].get_attribute('href')
        links_bar_title = links_bar[index].text
        links_bar[index].click()
        await asyncio.sleep(0.5)
        # verify that links on the topbar work, checking the titles of links
        if index == 0:
            assert links_bar_url.endswith("/hub/")
            if not value:
                assert (
                    f"hub/login?next={url_escape(app.base_url)}" in browser.current_url
                )
            else:
                u = app.users[orm.User.find(app.db, user)]
                while not u.spawner.ready:
                    await asyncio.sleep(1.5)
                assert f"/user/{user}/" in browser.current_url
                browser.back()
                assert value in browser.current_url
        elif index == 1:
            assert "/hub/home" in browser.current_url
            assert links_bar_title == "Home"
            if value not in browser.current_url:
                browser.back()
            assert value in browser.current_url
        elif index == 2:
            assert "/hub/token" in links_bar_url
            assert links_bar_title == "Token"
            assert links_bar_url in browser.current_url
            if value not in browser.current_url:
                browser.back()
        elif index == 3:
            assert links_bar_title == "Logout"
            assert links_bar_url.endswith("/hub/logout")
            assert "/login" in browser.current_url
            browser.back()


# SPAWNING


async def open_spawn_pending(app, browser, user, pass_w):
    url = url_path_join(public_host(app), app.hub.base_url, "/login?next=/hub/home")
    await in_thread(browser.get, url)
    await login(browser, user, pass_w)
    url_spawn = url_path_join(
        public_host(app), app.hub.base_url, '/spawn-pending/' + user
    )
    await in_thread(browser.get, url_spawn)
    await webdriver_wait(browser, EC.url_to_be(url_spawn))


async def test_spawn_pending_page(app, browser, user="test_user", pass_w="test_user"):
    # first request, no spawn is pending
    # spawn-pending shows button linking to spawn
    await open_spawn_pending(app, browser, user, pass_w)
    # on the page verify tbe button and expexted information
    assert is_displayed(browser, SpawningPageLocators.BUTTON_START_SERVER)

    buttons = browser.find_elements(*SpawningPageLocators.BUTTONS_SERVER)
    assert len(buttons) == 1
    for button in buttons:
        id = button.get_attribute('id')
        href_launch = button.get_attribute('href')
        name_button = button.text
    assert id == "start"
    assert name_button == SpawningPageLocators.BUTTON_LAUNCH_SERVER_NAME

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
    assert href_launch.endswith(f"/hub/spawn/{user}")


async def test_spawn_pending_launch_server_progress_process(
    app, browser, slow_spawn, user="test_user1", pass_w="test_user1"
):
    """verify that the server process messages are showing up to the user
    when the server is going to start up"""

    await open_spawn_pending(app, browser, user, pass_w)
    click(browser, SpawningPageLocators.BUTTON_START_SERVER)
    while is_displayed(browser, SpawningPageLocators.BUTTON_START_SERVER):
        await asyncio.sleep(0.001)
    while '/spawn-pending/' in browser.current_url and is_displayed(
        browser, SpawningPageLocators.PROGRESS_BAR
    ):
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
        # await asyncio.sleep(0.001)
        try:
            progress_bar = browser.find_element(*SpawningPageLocators.PROGRESS_BAR)
            progress = browser.find_elements(*SpawningPageLocators.PROGRESS_MESSAGE)
            logs = browser.find_elements(*SpawningPageLocators.PROGRESS_LOG)
            for status_message in progress:
                progress_messages = status_message.text
                percent = (
                    progress_bar.get_attribute('style')
                    .split(';')[0]
                    .split(':')[1]
                    .strip()
                )
                for i in range(len(logs)):
                    progress_log = logs[i].text
                    logs_list.append(progress_log)
                if progress_messages == "":
                    assert percent == "0%"
                    assert int(len(logs_list)) == 0
                if progress_messages == "Server requested":
                    assert percent == "0%"
                    assert int(len(logs_list)) == 1
                    assert str(logs_list[0]) == "Server requested"
                if progress_messages == "Spawning server...":
                    assert percent == "50%"
                    assert int(len(logs_list)) == 2
                    assert str(logs_list[0]) == "Server requested"
                    assert str(logs_list[1]) == "Spawning server..."
                if "Server ready at" in progress_messages:
                    assert (
                        f"Server ready at {app.base_url}user/{user}/"
                        in progress_messages
                    )
                    assert percent == "100%"
                    assert int(len(logs_list)) == 3
                    assert str(logs_list[0]) == "Server requested"
                    assert str(logs_list[1]) == "Spawning server..."
                    assert (
                        str(logs_list[2])
                        == f"Server ready at {app.base_url}user/{user}/"
                    )
                    assert str(logs_list[2]) == progress_messages
        except NoSuchElementException:
            break
        except StaleElementReferenceException:
            break
        await asyncio.sleep(0.001)


async def test_spawn_pending_launch_server(
    app, browser, user="test_user1", pass_w="test_user1"
):
    """verify that after a successful launch server via the spawn-pending page
    the user should see two buttons on the home page"""

    await open_spawn_pending(app, browser, user, pass_w)
    button = browser.find_element(*SpawningPageLocators.BUTTON_START_SERVER)
    u = app.users[orm.User.find(app.db, user)]
    click(browser, SpawningPageLocators.BUTTON_START_SERVER)
    await webdriver_wait(browser, EC.staleness_of(button))
    # checking that server is running and two butons present on the home page
    home_page = url_path_join(public_host(app), ujoin(app.base_url, "hub/home"))
    await in_thread(browser.get, home_page)
    assert u.spawner.ready
    assert is_displayed(browser, HomePageLocators.BUTTON_START_SERVER)
    assert is_displayed(browser, HomePageLocators.BUTTON_STOP_SERVER)


# HOME PAGE


async def open_home_page(app, browser, user, pass_w):
    """function to open the home page"""

    home_page = url_escape(app.base_url) + "hub/home"
    await open_url(app, browser, param="/login?next=" + home_page)
    await login(browser, user, pass_w)
    while '/hub/home' not in browser.current_url:
        await asyncio.sleep(0.5)


async def test_start_button_server_not_started(
    app, browser, user="test_user", pass_w="test_user"
):
    """verify that when server is not started one button is availeble,
    after starting 2 buttons are available"""
    await open_home_page(app, browser, user, pass_w)
    # checking that only one button is presented
    assert is_displayed(browser, HomePageLocators.BUTTON_START_SERVER)
    buttons = browser.find_elements(*HomePageLocators.BUTTONS_SERVER)
    assert len(buttons) == 1
    # checking link and name of the start button when server is going to be started
    for button in buttons:
        id = button.get_attribute('id')
        href_start = button.get_attribute('href')
        name_button = button.text
    assert id == "start"
    assert name_button == HomePageLocators.BUTTON_START_SERVER_NAME_DOWN
    assert href_start.endswith(f"/hub/spawn/{user}")

    # Start server via clicking on the Start button
    click(browser, HomePageLocators.BUTTON_START_SERVER)
    next_url = url_path_join(public_host(app), app.base_url, '/hub/home')
    await in_thread(browser.get, next_url)
    assert is_displayed(browser, HomePageLocators.BUTTON_START_SERVER)
    assert is_displayed(browser, HomePageLocators.BUTTON_STOP_SERVER)
    # verify that 2 buttons are displayed on the home page
    buttons = browser.find_elements(*HomePageLocators.BUTTONS_SERVER)
    if len(buttons) != 2:
        await webdriver_wait(browser, EC.visibility_of_all_elements_located(buttons))
    for button in buttons:
        id = button.get_attribute('id')
        href = button.get_attribute('href')
        style = button.get_attribute('style')
        assert not style
    # verify attributes of buttons
    assert buttons[0].get_attribute('id') == "stop"
    assert buttons[0].get_attribute('href') == None
    assert buttons[1].get_attribute('id') == "start"
    assert buttons[1].get_attribute('href').endswith(f"/user/{user}")
    assert elements_name(
        browser,
        HomePageLocators.BUTTON_STOP_SERVER,
        HomePageLocators.BUTTON_STOP_SERVER_NAME,
    )

    assert elements_name(
        browser,
        HomePageLocators.BUTTON_START_SERVER,
        HomePageLocators.BUTTON_START_SERVER_NAME,
    )


async def test_stop_button(app, browser, user="test_user", pass_w="test_user"):
    """verify that the stop button after stoping a server is not shown
    the start button is displayed with new name"""
    await open_home_page(app, browser, user, pass_w)
    if is_displayed(browser, HomePageLocators.BUTTON_START_SERVER) == True:
        click(browser, HomePageLocators.BUTTON_START_SERVER)
    next_url = url_path_join(public_host(app), app.base_url, '/hub/home')
    await in_thread(browser.get, next_url)

    buttons = browser.find_elements(*HomePageLocators.BUTTONS_SERVER)
    if len(buttons) != 2:
        await webdriver_wait(browser, EC.visibility_of_all_elements_located(buttons))

    u = app.users[orm.User.find(app.db, user)]
    while not u.spawner.ready:
        await asyncio.sleep(0.1)
    """add this stop click event is registred in JS to verify that the poccess is not still pending"""
    # Stop server via clicking on the Stop button
    click(browser, HomePageLocators.BUTTON_STOP_SERVER)
    # verify that the stop button is invisible on the page
    await webdriver_wait(
        browser, EC.invisibility_of_element_located(HomePageLocators.BUTTON_STOP_SERVER)
    )
    buttons = browser.find_elements(*HomePageLocators.BUTTONS_SERVER)
    assert len(buttons) == 2
    # checking attributes of buttons after server was stopped
    for button in buttons:
        id = button.get_attribute('id')
        href = button.get_attribute('href')
        style = button.get_attribute('style')
    assert buttons[0].get_attribute('id') == "stop"
    assert buttons[0].get_attribute('style') == "display: none;"
    assert buttons[0].get_attribute('href') == None
    assert buttons[1].get_attribute('id') == "start"
    assert buttons[1].get_attribute('href').endswith(f"/hub/spawn/{user}")
    assert buttons[1].text == HomePageLocators.BUTTON_START_SERVER_NAME_DOWN


# TOKEN PAGE
async def open_token_page(app, browser, user, pass_w):
    """function to open the token page"""

    token_page = url_escape(app.base_url) + "hub/token"
    await open_url(app, browser, param="/login?next=" + token_page)
    await login(browser, user, pass_w)
    while '/hub/token' not in browser.current_url:
        await asyncio.sleep(0.5)


def elements_table(browser):
    return browser.find_element(*TokenPageLocators.TABLE_API)


def elements_table_body(browser):
    table = browser.find_element(*TokenPageLocators.TABLE_API)
    return table.find_element(*TokenPageLocators.TABLE_API_BODY)


def elements_row_body(browser):
    table = browser.find_element(*TokenPageLocators.TABLE_API)
    body = table.find_element(*TokenPageLocators.TABLE_API_BODY)
    return body.find_elements(*TokenPageLocators.TABLE_API_ROWS_BY_CLASS)


def elements_row_head(browser):
    table = browser.find_element(*TokenPageLocators.TABLE_API)
    head = table.find_element(*TokenPageLocators.TABLE_API_HEAD)
    return head.find_elements(*TokenPageLocators.TABLE_API_ROWS)


async def test_elements_of_token_page_server_not_started(
    app, browser, user="test_user123", pass_w="test_user123"
):

    """verify elements of the request token form and the token page
    when the server is not started and no token was requested"""
    await open_token_page(app, browser, user, pass_w)
    ### Request token form ###
    assert is_displayed(browser, TokenPageLocators.BUTTON_API_REQ)
    button_api_req_text = browser.find_element(
        *TokenPageLocators.BUTTON_API_REQ
    ).get_attribute('innerHTML')
    assert button_api_req_text.strip() == TokenPageLocators.BUTTON_API_REQ_NAME
    assert is_displayed(browser, TokenPageLocators.INPUT_TOKEN)
    # verify that Note field is editable
    send_text(browser, TokenPageLocators.INPUT_TOKEN, "test_text")
    assert (
        browser.find_element(*TokenPageLocators.INPUT_TOKEN).get_attribute('value')
        == "test_text"
    )
    clear(browser, TokenPageLocators.INPUT_TOKEN)
    assert (
        browser.find_element(*TokenPageLocators.INPUT_TOKEN).get_attribute('value')
        == ""
    )

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
    Dict_opt_list = {}
    for option in option_elements:
        Dict_opt_list[option.text] = option.get_attribute('value')

    assert Dict_opt_list == TokenPageLocators.LIST_EXP_TOKEN_OPT_DICT
    # checking that no API Tokens and Authorized Applications
    assert not is_displayed(browser, TokenPageLocators.TABLE_API)
    assert not is_displayed(browser, TokenPageLocators.TABLE_AUTH)


async def test_token_server_started(
    app, browser, user="test_user123", pass_w="test_user123"
):
    """verify API Tokens table contant in case the server is started"""

    await open_home_page(app, browser, user, pass_w)
    if is_displayed(browser, HomePageLocators.BUTTON_START_SERVER):
        # Start server via clicking on the Start button
        click(browser, HomePageLocators.BUTTON_START_SERVER)
    next_url = url_path_join(public_host(app), app.base_url, '/hub/token')
    await in_thread(browser.get, next_url)
    # verify that the tokens page elements are displayed
    assert is_displayed(browser, TokenPageLocators.BUTTON_API_REQ)
    assert is_displayed(browser, TokenPageLocators.INPUT_TOKEN)
    assert not is_displayed(browser, TokenPageLocators.PANEL_AREA)
    assert is_displayed(browser, TokenPageLocators.TABLE_API)
    # API Tokens table
    Dict_body_rows = {}
    Dict_body_columns = {}
    for i in range(len(elements_row_body(browser))):
        await asyncio.sleep(1)
        Dict_body_rows[i] = elements_row_body(browser)[i].text
        columns_body = elements_row_body(browser)[i].find_elements(
            *TokenPageLocators.TABLE_API_COLUMNS
        )
        for j in range(len(columns_body)):
            Dict_body_columns[j] = columns_body[j].text

    assert is_displayed(browser, TokenPageLocators.TABLE_API_COLUMNS)
    assert int(len(columns_body)) == 5
    # verify that colunms values
    note = Dict_body_columns.get(0)
    last_used = Dict_body_columns.get(1)
    expires_at = Dict_body_columns.get(3)
    assert note == "Server at " + ujoin(app.base_url, f"/user/{user}/")
    assert (last_used and expires_at) == "Never"


async def test_request_new_token_token_panel(
    app, browser, user="test_user", pass_w="test_user"
):
    """verify that after requesting token via the button
    a panel with new token is displayed
    and it will be hidden after refreshing of the page"""

    await open_token_page(app, browser, user, pass_w)
    # fill in the note field
    send_text(browser, TokenPageLocators.INPUT_TOKEN, "note_value")
    assert (
        browser.find_element(*TokenPageLocators.INPUT_TOKEN).get_attribute('value')
        == "note_value"
    )
    await asyncio.sleep(1)
    # request the token via the button
    click(browser, TokenPageLocators.BUTTON_API_REQ)
    # verify that "Your new API Token" panel shows up with the new API token
    await webdriver_wait(
        browser, EC.visibility_of_element_located(TokenPageLocators.PANEL_AREA)
    )
    assert not browser.find_element(*TokenPageLocators.PANEL_AREA).get_attribute(
        'style'
    )
    assert (
        browser.find_element(*TokenPageLocators.PANEL_TOKEN).text
        == TokenPageLocators.PANEL_TOKEN_TITLE
    )
    assert browser.find_element(*TokenPageLocators.RESULT_TOKEN) is not empty
    # refresh the page
    await in_thread(browser.get, browser.current_url)
    # verify that "Your new API Token" panel is hidden after refresh the page
    await webdriver_wait(
        browser, EC.invisibility_of_element_located(TokenPageLocators.PANEL_AREA)
    )
    assert (
        browser.find_element(*TokenPageLocators.PANEL_AREA).get_attribute('style')
        == "display: none;"
    )
    assert browser.find_element(*TokenPageLocators.TABLE_API).is_displayed()


@pytest.mark.parametrize(
    "token_opt, note, note_value, user, pass_w",
    [
        ("1 Hour", True, "test_text", "test_user", "test_user"),
        ("1 Hour", False, "test_text", "test_user", "test_user"),
        ("1 Day", True, "test_text", "test_user", "test_user"),
        ("1 Day", False, "test_text", "test_user", "test_user"),
        ("1 Week", True, "test_text", "test_user", "test_user"),
        ("1 Week", False, "test_text", "test_user", "test_user"),
        ("Never", True, "test_text", "test_user", "test_user"),
        ("Never", False, "test_text", "test_user", "test_user"),
    ],
)
async def test_request_token_duration(
    app, browser, token_opt, note, note_value, user, pass_w
):
    """verify request token with the different options"""
    await open_token_page(app, browser, user, pass_w)
    is_displayed(browser, TokenPageLocators.LIST_EXP_TOKEN_FIELD)

    # select the token duration
    select_element = browser.find_element(*TokenPageLocators.LIST_EXP_TOKEN_FIELD)
    while token_opt != "Never":
        select = Select(select_element)
        select.select_by_visible_text(token_opt)
        break
    if note == True:
        send_text(browser, TokenPageLocators.INPUT_TOKEN, note_value)
        assert (
            browser.find_element(*TokenPageLocators.INPUT_TOKEN).get_attribute('value')
            == note_value
        )
    else:
        pass
    await asyncio.sleep(1)
    click(browser, TokenPageLocators.BUTTON_API_REQ)
    # refresh the page
    await in_thread(browser.get, browser.current_url)
    # API Tokens table: verify that elements are displayed
    assert is_displayed(browser, TokenPageLocators.TABLE_API)
    assert is_displayed(browser, TokenPageLocators.TABLE_API_HEAD)
    assert is_displayed(browser, TokenPageLocators.TABLE_API_BODY)
    assert int(len(elements_row_head(browser))) == 1
    assert int(len(elements_row_body(browser))) == 1
    List_rows_head = []
    List_col_head = []
    # verify head of table rows
    for row_head in elements_row_head(browser):
        i = row_head.text
        List_rows_head.append(i)
        columns_head = elements_row_head(browser)[0].find_elements(
            *TokenPageLocators.TABLE_API_COLUMNS
        )
        for column_head in columns_head:
            j = column_head.text
            List_col_head.append(j)

    assert List_col_head == TokenPageLocators.TABLE_API_HEAD_LIST
    # verify body of table
    Dict_body_rows = {}
    Dict_body_columns = {}
    for i in range(len(elements_row_body(browser))):
        await asyncio.sleep(1)
        Dict_body_rows[i] = elements_row_body(browser)[i].text
        columns_body = elements_row_body(browser)[i].find_elements(
            *TokenPageLocators.TABLE_API_COLUMNS
        )
        for j in range(len(columns_body)):
            Dict_body_columns[j] = columns_body[j].text
    assert is_displayed(browser, TokenPageLocators.TABLE_API_COLUMNS)
    assert int(len(columns_head)) == 4
    assert int(len(columns_body)) == 5

    if note == False:
        assert Dict_body_columns.get(0) == TokenPageLocators.TEXT_WOUT_NOTE
    else:
        assert Dict_body_columns.get(0) == note_value
    if token_opt == "Never":
        assert Dict_body_columns.get(3) == "Never"
    elif token_opt == "1 Hour":
        assert Dict_body_columns.get(3) == "in an hour"
    elif token_opt == "1 Day":
        assert Dict_body_columns.get(3) == "in a day"
    elif token_opt == "1 Week":
        assert Dict_body_columns.get(3) == "in 7 days"
    # verify that the button for revoke is presented
    buttons = elements_table_body(browser).find_elements(
        *TokenPageLocators.BUTTON_REVOKE
    )
    for button in buttons:
        button = button.text
    assert button == columns_body[len(columns_body) - 1].text
    assert int(len(buttons)) == 1


@pytest.mark.parametrize(
    "token_type, user, pass_w",
    [
        ("server_up", "test_user", "test_user"),
        ("request", "test_user", "test_user"),
        ("both", "test_user", "test_user"),
    ],
)
async def test_revoke_token(app, browser, token_type, user, pass_w):
    """verify API Tokens table contant in case the server is started"""

    await open_home_page(app, browser, user, pass_w)
    if token_type == "server_up" or token_type == "both":
        if is_displayed(browser, HomePageLocators.BUTTON_START_SERVER):
            # Start server via clicking on the Start button
            click(browser, HomePageLocators.BUTTON_START_SERVER)
    next_url = url_path_join(public_host(app), app.base_url, '/hub/token')
    await in_thread(browser.get, next_url)
    await asyncio.sleep(1)
    if token_type == "both" or token_type == "request":
        click(browser, TokenPageLocators.BUTTON_API_REQ)
        await asyncio.sleep(1)
        # refresh the page
        await in_thread(browser.get, browser.current_url)
    buttons = elements_table_body(browser).find_elements(
        *TokenPageLocators.BUTTON_REVOKE
    )
    # verify that the token revoked
    if token_type == "server_up" or token_type == "request":
        assert int(len(buttons)) == 1
        await asyncio.sleep(1)
        click(browser, TokenPageLocators.BUTTON_REVOKE)
        await webdriver_wait(
            browser, EC.invisibility_of_element_located(TokenPageLocators.BUTTON_REVOKE)
        )
        buttons = elements_table_body(browser).find_elements(
            *TokenPageLocators.BUTTON_REVOKE
        )
        assert is_displayed(browser, TokenPageLocators.TABLE_API_HEAD)
        assert int(len(elements_row_head(browser))) == 1
        assert (int(len(elements_row_body(browser))) and int(len(buttons))) == 0
    else:
        # verify that both tokens are revoked
        assert int(len(buttons)) == 2
        while int(len(buttons)) != 0:
            await asyncio.sleep(0.5)
            click(browser, TokenPageLocators.BUTTON_REVOKE)
            await asyncio.sleep(0.5)
            buttons = elements_table_body(browser).find_elements(
                *TokenPageLocators.BUTTON_REVOKE
            )
            assert int(len(buttons)) == int(len(elements_row_body(browser)))
        assert int(len(buttons)) == 0


# LOGOUT


@pytest.mark.parametrize(
    "url",
    [("/hub/home"), ("/hub/token")],
)
async def test_user_logout(app, browser, url, user="test_user", pass_w="test_user"):
    next_url = ujoin(url_escape(app.base_url) + url)
    await open_url(app, browser, param="/login?next=" + next_url)
    await login(browser, user, pass_w)
    await webdriver_wait(
        browser, EC.presence_of_all_elements_located(BarLocators.LINK_HOME_BAR)
    )
    click(browser, BarLocators.BUTTON_LOGOUT)
    await webdriver_wait(browser, EC.url_changes(browser.current_url))
    # checking url changing to login url and login form is displayed
    assert 'hub/login' in browser.current_url
    assert is_displayed(browser, LoginPageLocators.FORM_LOGIN)
    elements_home_bar = browser.find_elements(*BarLocators.LINK_HOME_BAR)
    assert len(elements_home_bar) == 1  # including 1 element
    for element_home_bar in elements_home_bar:
        assert element_home_bar.get_attribute('href').endswith('hub/')
    # verify that user can login after logout
    await login(browser, user, pass_w)
    if f"/user/{user}/" not in browser.current_url:
        await webdriver_wait(browser, EC.url_changes(browser.current_url))
    else:
        pass
    assert f"/user/{user}" in browser.current_url
