"""Tests for the Selenium WebDriver"""

import asyncio
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

from jupyterhub.tests.selenium.locators import (
    BarLocators,
    HomePageLocators,
    LoginPageLocators,
    SpawningPageLocators,
    TokenPageLocators,
)
from jupyterhub.utils import exponential_backoff

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


def clear(browser, by_locator):
    """wait for element to be presented, then clear the text in it"""

    return (
        WebDriverWait(browser, 10)
        .until(EC.presence_of_element_located(by_locator))
        .clear()
    )


def elements_name(browser, by_locator, text):
    """wait for element to be contained expected text"""

    return WebDriverWait(browser, 10).until(
        EC.text_to_be_present_in_element(by_locator, text)
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
    await click(browser, LoginPageLocators.LOGIN_BUTTON)
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
    assert browser.title == LoginPageLocators.PAGE_TITLE
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
    error = browser.find_element(*LoginPageLocators.ERROR_INVALID_CREDANTIALS)
    # verify error message and url
    assert LoginPageLocators.ERROR_MESSAGES_LOGIN == error.text
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
    await wait_for_ready(browser)


async def test_spawn_pending_server_not_started(
    app, browser, slow_spawn, no_patience, user
):
    # first request, no spawn is pending
    # spawn-pending shows button linking to spawn
    await open_spawn_pending(app, browser, user)
    # on the page verify the button and expected information
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
    assert href_launch.endswith(f"/hub/spawn/{user.name}")


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
        vis = EC.visibility_of_element_located(SpawningPageLocators.PROGRESS_BAR)(
            browser
        ).is_displayed()
        return vis or '/spawn-pending/' not in browser.current_url

    await webdriver_wait(browser, wait_for_progress)
    # make sure we're still on the spawn-pending page
    assert '/spawn-pending/' in browser.current_url
    while '/spawn-pending/' in browser.current_url:
        progress_message = browser.find_element(
            *SpawningPageLocators.PROGRESS_MESSAGE
        ).text
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
            progress_bar = browser.find_element(*SpawningPageLocators.PROGRESS_BAR)
            progress = browser.find_element(*SpawningPageLocators.PROGRESS_MESSAGE)
            logs = browser.find_elements(*SpawningPageLocators.PROGRESS_LOG)
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
    button = browser.find_element(*SpawningPageLocators.BUTTON_START_SERVER)
    await click(browser, SpawningPageLocators.BUTTON_START_SERVER)
    await webdriver_wait(browser, EC.staleness_of(button))
    # checking that server is running and two butons present on the home page
    home_page = url_path_join(public_host(app), ujoin(app.base_url, "hub/home"))
    await in_thread(browser.get, home_page)
    while not user.spawner.ready:
        await asyncio.sleep(0.01)
    assert is_displayed(browser, HomePageLocators.BUTTON_START_SERVER)
    assert is_displayed(browser, HomePageLocators.BUTTON_STOP_SERVER)


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
    await wait_for_ready(browser)


async def test_start_button_server_not_started(app, browser, user):
    """verify that when server is not started one button is availeble,
    after starting 2 buttons are available"""
    await open_home_page(app, browser, user)
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
    assert href_start.endswith(f"/hub/spawn/{user.name}")

    # Start server via clicking on the Start button
    await click(browser, HomePageLocators.BUTTON_START_SERVER)
    next_url = url_path_join(public_host(app), app.base_url, '/hub/home')
    await in_thread(browser.get, next_url)
    await wait_for_ready(browser)
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
    assert buttons[1].get_attribute('href').endswith(f"/user/{user.name}")
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


async def test_stop_button(app, browser, user):
    """verify that the stop button after stoping a server is not shown
    the start button is displayed with new name"""
    await open_home_page(app, browser, user)

    if is_displayed(browser, HomePageLocators.BUTTON_START_SERVER):
        await click(browser, HomePageLocators.BUTTON_START_SERVER)
    next_url = url_path_join(public_host(app), app.base_url, '/hub/home')
    await in_thread(browser.get, next_url)
    await wait_for_ready(browser)
    buttons = browser.find_elements(*HomePageLocators.BUTTONS_SERVER)
    if len(buttons) != 2:
        await webdriver_wait(browser, EC.visibility_of_all_elements_located(buttons))
    while not user.spawner.ready:
        # added this stop click event is registered in JS to verify that the process is not still pending
        await asyncio.sleep(0.1)
    # Stop server via clicking on the Stop button
    await click(browser, HomePageLocators.BUTTON_STOP_SERVER)
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
    assert buttons[1].get_attribute('href').endswith(f"/hub/spawn/{user.name}")
    assert buttons[1].text == HomePageLocators.BUTTON_START_SERVER_NAME_DOWN


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


def elements_API_tokens_table(browser):
    """function to get table of tokens as element
    and getting the attributes for each tokens"""
    try:
        return browser.find_element(*TokenPageLocators.TABLE_API)
    except NoSuchElementException:
        return WebDriverWait(browser, 10).until(
            EC.presence_of_element_located(TokenPageLocators.TABLE_API)
        )


def elements_API_tokens_table_body(browser):
    """function to get body table of tokens as element
    and getting the attributes for each tokens"""
    try:
        table = elements_API_tokens_table(browser)
        return table.find_element(*TokenPageLocators.TABLE_API_BODY)
    except NoSuchElementException:
        return WebDriverWait(browser, 10).until(
            EC.presence_of_element_located(TokenPageLocators.TABLE_API_BODY)
        )


def elements_API_tokens_row_body(browser):
    """function to get table rows of tokens as elements
    and getting the attributes for each tokens"""
    try:
        body = elements_API_tokens_table_body(browser)
        return body.find_elements(*TokenPageLocators.TABLE_API_ROWS_BY_CLASS)
    except NoSuchElementException:
        return WebDriverWait(browser, 10).until(
            EC.presence_of_all_elements_located(
                TokenPageLocators.TABLE_API_ROWS_BY_CLASS
            )
        )


def elements_API_tokens_row_head(browser):
    """function to get table heads of tokens as elements
    and getting the attributes for tables head"""
    try:
        table = elements_API_tokens_table(browser)
        head = table.find_element(*TokenPageLocators.TABLE_API_HEAD)
        return head.find_elements(*TokenPageLocators.TABLE_API_ROWS)
    except NoSuchElementException:
        return WebDriverWait(browser, 10).until(
            EC.presence_of_all_elements_located(TokenPageLocators.TABLE_API_ROWS)
        )


async def table_dict_row(browser):
    """function to insert table elements into table dictionary by rows"""
    dict_body_rows = {}
    for i in range(len(elements_API_tokens_row_body(browser))):
        dict_body_rows[i] = elements_API_tokens_row_body(browser)[i].text
    return dict_body_rows


async def table_dict_columns(browser):
    """function to insert table elements into table dictionary by columns"""
    dict_body_columns = {}
    for i in range(len(elements_API_tokens_row_body(browser))):
        columns_body = elements_API_tokens_row_body(browser)[i].find_elements(
            *TokenPageLocators.TABLE_API_COLUMNS
        )
        for j in range(len(columns_body)):
            dict_body_columns[j] = columns_body[j].text
    return dict_body_columns


async def test_token_request_form_and_panel(app, browser, cleanup_after, user):
    """verify elements of the request token form"""
    await open_token_page(app, browser, user)
    is_displayed(browser, TokenPageLocators.BUTTON_API_REQ)
    button_api_req_text = browser.find_element(
        *TokenPageLocators.BUTTON_API_REQ
    ).get_attribute('innerHTML')
    assert button_api_req_text.strip() == TokenPageLocators.BUTTON_API_REQ_NAME
    is_displayed(browser, TokenPageLocators.LIST_EXP_TOKEN_FIELD)
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
    assert (
        browser.find_element(*TokenPageLocators.INPUT_TOKEN).get_attribute('value')
        == ""
    )
    await click(browser, TokenPageLocators.BUTTON_API_REQ)
    await webdriver_wait(
        browser, EC.visibility_of_element_located(TokenPageLocators.PANEL_AREA)
    )
    # verify that "Your new API Token" panel shows up with the new API token
    assert is_displayed(browser, TokenPageLocators.PANEL_AREA)
    assert not browser.find_element(*TokenPageLocators.PANEL_AREA).get_attribute(
        'style'
    )
    assert (
        browser.find_element(*TokenPageLocators.PANEL_TOKEN).text
        == TokenPageLocators.PANEL_TOKEN_TITLE
    )
    assert browser.find_element(*TokenPageLocators.RESULT_TOKEN)
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
        await open_home_page(app, browser, user)
        assert "/hub/home" in browser.current_url
        # Start server via clicking on the Start button
        await click(browser, HomePageLocators.BUTTON_START_SERVER)
        while not user.spawner.ready:
            await asyncio.sleep(0.01)
        next_url = url_path_join(public_host(app), app.base_url, '/hub/token')
        await in_thread(browser.get, next_url)
    else:
        await open_token_page(app, browser, user)
        is_displayed(browser, TokenPageLocators.LIST_EXP_TOKEN_FIELD)
        # select the token duration
        select_element = browser.find_element(*TokenPageLocators.LIST_EXP_TOKEN_FIELD)
        while token_opt != ("Never" and "server_up"):
            select = Select(select_element)
            select.select_by_visible_text(token_opt)
            break
        if note:
            send_text(browser, TokenPageLocators.INPUT_TOKEN, note)
            assert (
                browser.find_element(*TokenPageLocators.INPUT_TOKEN).get_attribute(
                    'value'
                )
                == note
            )
        else:
            assert (
                browser.find_element(*TokenPageLocators.INPUT_TOKEN).get_attribute(
                    'value'
                )
                == ""
            )
        await asyncio.sleep(0.1)
        await click(browser, TokenPageLocators.BUTTON_API_REQ)
        await webdriver_wait(
            browser, EC.visibility_of_element_located(TokenPageLocators.PANEL_AREA)
        )
        # getting the token_id
        token = browser.find_element(*TokenPageLocators.RESULT_TOKEN).text
        # refresh the page
        await in_thread(browser.get, browser.current_url)
        # wait for javascript, moment.js to format
        await wait_for_ready(browser)
    # API Tokens table: verify that elements are displayed
    assert is_displayed(browser, TokenPageLocators.TABLE_API)
    assert is_displayed(browser, TokenPageLocators.TABLE_API_HEAD)
    assert is_displayed(browser, TokenPageLocators.TABLE_API_BODY)
    assert len(elements_API_tokens_row_head(browser)) == 1
    assert len(elements_API_tokens_row_body(browser)) == 1
    List_rows_head = []
    List_col_head = []
    # verify head of table rows
    for row_head in elements_API_tokens_row_head(browser):
        i = row_head.text
        List_rows_head.append(i)
        columns_head = elements_API_tokens_row_head(browser)[0].find_elements(
            *TokenPageLocators.TABLE_API_COLUMNS
        )
        for column_head in columns_head:
            j = column_head.text
            List_col_head.append(j)
    assert List_col_head == TokenPageLocators.TABLE_API_HEAD_LIST
    # verify the body of the API table
    dict_body_columns = await table_dict_columns(browser)
    assert is_displayed(browser, TokenPageLocators.TABLE_API_COLUMNS)
    assert len(columns_head) == 4
    assert len(dict_body_columns) == 5
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
    note_on_page = dict_body_columns.get(0)
    assert note_on_page == expected_note
    expires_at_text = dict_body_columns.get(3)
    last_used_text = dict_body_columns.get(1)
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
    revoke_button = elements_API_tokens_table_body(browser).find_elements(
        *TokenPageLocators.BUTTON_REVOKE
    )[0]
    revoke_button.text == "revoke"


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

    await open_home_page(app, browser, user)
    if token_type == "server_up" or token_type == "both":
        assert "/hub/home" in browser.current_url
        # Start server via clicking on the Start button
        await click(browser, HomePageLocators.BUTTON_START_SERVER)
        while not user.spawner.ready:
            await asyncio.sleep(0.01)
    next_url = url_path_join(public_host(app), app.base_url, '/hub/token')
    await in_thread(browser.get, next_url)
    assert next_url in browser.current_url
    if token_type == "both" or token_type == "request_by_user":
        await asyncio.sleep(0.1)
        await click(browser, TokenPageLocators.BUTTON_API_REQ)
        await webdriver_wait(
            browser, EC.visibility_of_element_located(TokenPageLocators.PANEL_AREA)
        )
        # refresh the page
        await in_thread(browser.get, browser.current_url)
    await wait_for_ready(browser)
    buttons = elements_API_tokens_table_body(browser).find_elements(
        *TokenPageLocators.BUTTON_REVOKE
    )
    await webdriver_wait(
        browser, EC.visibility_of_all_elements_located(TokenPageLocators.BUTTON_REVOKE)
    )
    # verify that the token revoked from UI and the database
    if token_type in {"server_up", "request_by_user"}:
        assert len(buttons) == 1
        assert len(user.api_tokens) == 1
        await click(browser, TokenPageLocators.BUTTON_REVOKE)
        await webdriver_wait(
            browser,
            EC.none_of(
                EC.presence_of_all_elements_located(
                    TokenPageLocators.TABLE_API_ROWS_BY_CLASS
                )
            ),
        )
        buttons = elements_API_tokens_table_body(browser).find_elements(
            *TokenPageLocators.BUTTON_REVOKE
        )
        assert is_displayed(browser, TokenPageLocators.TABLE_API_HEAD)
        assert len(elements_API_tokens_row_head(browser)) == 1
        assert len(elements_API_tokens_row_body(browser)) == 0
        assert len(buttons) == 0
        assert len(user.api_tokens) == 0
    if token_type == "both":
        # verify that both tokens are revoked from UI and the database
        assert len(buttons) == 2
        assert len(user.api_tokens) == 2
        while len(buttons) != 0:
            await click(browser, TokenPageLocators.BUTTON_REVOKE)
            # wait for the row with revoked token disappears
            await asyncio.sleep(0.1)
            buttons = elements_API_tokens_table_body(browser).find_elements(
                *TokenPageLocators.BUTTON_REVOKE
            )
            assert len(buttons) == len(elements_API_tokens_row_body(browser))
        assert len(buttons) == 0
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
    logo = browser.find_element(*BarLocators.LOGO)
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
        if index == 0:
            assert links_bar_url.endswith("/hub/")
            if not page:
                assert (
                    f"hub/login?next={url_escape(app.base_url)}" in browser.current_url
                )
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
        elif index == 1:
            assert "/hub/home" in browser.current_url
            assert links_bar_title == "Home"
            if page not in browser.current_url:
                browser.back()
            assert page in browser.current_url
        elif index == 2:
            assert "/hub/token" in links_bar_url
            assert links_bar_title == "Token"
            assert links_bar_url in browser.current_url
            if page not in browser.current_url:
                browser.back()
        elif index == 3:
            assert links_bar_title == "Logout"
            assert links_bar_url.endswith("/hub/logout")
            assert "/login" in browser.current_url
            browser.back()


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
    await click(browser, BarLocators.BUTTON_LOGOUT)
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
