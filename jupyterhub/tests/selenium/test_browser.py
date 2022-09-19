import asyncio
import time
from functools import partial

import pytest
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.color import Color
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
from ..utils import get_page, public_host, public_url, ujoin

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


# initiate to open login page
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


def elements_name(browser, by_locator, text):
    return WebDriverWait(browser, 10).until(
        EC.text_to_be_present_in_element(by_locator, text)
    )


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

    # verify title / url
    assert browser.title == LoginPageLocators.PAGE_TITLE
    assert form.endswith(form_action)
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

    # verify error message and url
    assert LoginPageLocators.ERROR_MESSAGES_LOGIN == error.text
    assert 'hub/login' in browser.current_url


# HOME PAGE
async def open_home_page(app, browser, user="test_user", pass_w="test_user"):

    """await open_url(app, browser)
    redirected_url = url_path_join(public_host(app), app.base_url, '/hub/home')
    await login(browser, user, pass_w)
    await in_thread(browser.get, redirected_url)"""

    url = url_path_join(public_host(app), app.hub.base_url, "/login?next=/hub/home")
    await in_thread(browser.get, url)
    redirected_url = url_path_join(public_host(app), app.base_url, '/hub/home')
    await login(browser, user, pass_w)
    await in_thread(browser.get, redirected_url)
    # verify home page is opened and  contains username
    if '/hub/home' not in browser.current_url:
        await webdriver_wait(browser, EC.url_to_be(redirected_url))
    else:
        pass
    assert browser.current_url == redirected_url


async def test_open_home_Opage(app, browser):
    await open_home_page(app, browser, user="test_user", pass_w="test_user")
    assert '/hub/home' in browser.current_url
    # navigate_bar: checking links
    links_bar = browser.find_elements(*HomePageLocators.LINK_HOME_BAR)
    for link in links_bar:
        link.get_attribute('href')
        print(link.get_attribute('href'))
        """if not link.get_attribute('href').endswith('hub/'):
            result = requests.head(link.get_attribute('href'))
            print(result)
            if result.status_code != 200:
                print(link.get_attribute('href'), result.status_code)
        else:
            pass        
        #assert result.status_code == 200
        """
    # buttons: two buttons are on the page
    assert is_displayed(browser, HomePageLocators.BUTTON_STOP_SERVER) == True
    assert is_displayed(browser, HomePageLocators.BUTTON_START_SERVER) == True

    buttons = browser.find_elements(*HomePageLocators.BUTTONS_SERVER)
    for button in buttons:
        id = button.get_attribute('id')
        style = button.get_attribute('style')
        assert not style == True
    assert buttons[0].get_attribute('id') == "stop"
    assert buttons[1].get_attribute('id') == "start"
    assert (
        elements_name(
            browser,
            HomePageLocators.BUTTON_STOP_SERVER,
            HomePageLocators.BUTTON_STOP_SERVER_NAME,
        )
        == True
    )
    assert (
        elements_name(
            browser,
            HomePageLocators.BUTTON_START_SERVER,
            HomePageLocators.BUTTON_START_SERVER_NAME,
        )
        == True
    )
    # EC.text_to_be_present_in_element_value(HomePageLocators.BUTTON_STOP_SERVER, text_)


async def test_open_home_page(app, browser):
    user = "test_user"
    await open_home_page(app, browser, user="test_user", pass_w="test_user")
    assert '/hub/home' in browser.current_url
    # navigate_bar: checking links
    links_bar = browser.find_elements(*HomePageLocators.LINK_HOME_BAR)
    for link in links_bar:
        link.get_attribute('href')
        print(link.get_attribute('href'))
        """if not link.get_attribute('href').endswith('hub/'):
            result = requests.head(link.get_attribute('href'))
            print(result)
            if result.status_code != 200:
                print(link.get_attribute('href'), result.status_code)
        else:
            pass        
        #assert result.status_code == 200
        """
    """to be done - add checking if server is not up and not running"""
    # buttons: only Start button is on the page
    assert is_displayed(browser, HomePageLocators.BUTTON_START_SERVER) == True
    buttons = browser.find_elements(*HomePageLocators.BUTTONS_SERVER)
    assert len(buttons) == 1
    for button in buttons:
        id = button.get_attribute('id')
        href_start = button.get_attribute('href')
        name_button = button.text
    assert id == "start"
    assert name_button == HomePageLocators.BUTTON_START_SERVER_NAME_DOWN
    assert href_start.endswith(f"/hub/spawn/{user}")


async def test_buttons_stop_start(app, browser):
    user = "test_user"
    await open_home_page(app, browser, user="test_user", pass_w="test_user")
    is_displayed(browser, HomePageLocators.BUTTON_START_SERVER)

    # checking link of start button when server is started
    href_start = browser.find_element(
        *HomePageLocators.BUTTON_START_SERVER
    ).get_attribute('href')
    assert href_start.endswith(f"/hub/spawn/{user}")

    """Start server"""

    click(browser, HomePageLocators.BUTTON_START_SERVER)
    # spawn redirects to the spawn-pending page
    next_url = ujoin(app.hub.base_url, '/spawn-pending', user)
    spawn_url = url_concat('/spawn/' + user, dict(next=next_url))
    await in_thread(browser.get, url_path_join(public_host(app), next_url))
    await webdriver_wait(browser, EC.url_to_be(browser.current_url))

    assert browser.current_url == url_path_join(public_host(app), next_url)

    # check elements on the spawn-pending page
    texts = browser.find_elements(*HomePageLocators.TEXT_SERVER)
    texts_list = []
    for text in texts:
        text.text
        texts_list.append(text.text)

    assert str(texts_list[0]) == HomePageLocators.TEXT_SERVER_STARTING
    assert str(texts_list[1]) == HomePageLocators.TEXT_SERVER_REDIRECT

    next_url = ujoin(app.hub.base_url, '/home')
    await in_thread(browser.get, url_path_join(public_host(app), next_url))
    await webdriver_wait(browser, EC.url_to_be(browser.current_url))
    # checking that 2 buttons are pressed
    assert is_displayed(browser, HomePageLocators.BUTTON_START_SERVER) == True
    assert is_displayed(browser, HomePageLocators.BUTTON_STOP_SERVER) == True

    buttons = browser.find_elements(*HomePageLocators.BUTTONS_SERVER)
    assert len(buttons) == 2

    await asyncio.sleep(1)
    """add this stop click event is registred in JS"""

    click(browser, HomePageLocators.BUTTON_STOP_SERVER)

    # next_url = ujoin(app.hub.base_url, '/home')
    # await in_thread(browser.get, url_path_join(public_host(app), next_url))

    el = browser.find_element(*HomePageLocators.BUTTON_STOP_SERVER)

    # await webdriver_wait(browser, EC.url_changes(browser.current_url))

    await webdriver_wait(browser, EC.invisibility_of_element(el))

    # await webdriver_wait(browser, EC.url_changes(browser.current_url))

    # stop_b=browser.find_element(*HomePageLocators.BUTTON_STOP_SERVER)
    # print(stop_b.get_attribute('class'))

    # webdriver.ActionChains(browser).move_to_element(stop_b).perform()
    # webdriver.ActionChains(browser).double_click(stop_b).perform()
    # injected_javascript=("require(['home']);")
    # browser.execute_async_script(injected_javascript)
    # browser.execute_async_script("document.stopServer()")
    # browser.set_script_timeout(4000)
    # browser.execute_async_script("""$("#stop").click(function () {$("#start").attr("disabled", true).attr("title", "Your server is stopping").click(function () {return false;});api.stop_server(user, {success: function () {$("#stop").hide();$("#start").text("Start My Server").attr("title", "Start your default server").attr("disabled", false).attr("href", base_url + "spawn/" + user).off("click");},});});""")

    """browser.execute_async_script('''
    var row = getRow($(this));
    var serverName = row.data("server-name");

    // before request
    disableRow(row);

    // request
    api.stop_named_server(user, serverName, {
      success: function () {
        enableRow(row, false);
      },
    });''')"""

    # browser.execute_script("return jQuery.active==0")

    """await webdriver_wait(
        browser, EC.visibility_of_element_located(HomePageLocators.BUTTON_STOP_SERVER)
    )
    assert is_displayed(browser, HomePageLocators.BUTTON_STOP_SERVER) == True

    el=browser.find_element(*HomePageLocators.BUTTON_STOP_SERVER)
    await webdriver_wait(browser, EC.invisibility_of_element(el))
    print(await webdriver_wait(browser, EC.invisibility_of_element(el)))
    #time.sleep(20)"""

    """# checking link of start button when server is stopped
    href_start = browser.find_element(
        *HomePageLocators.BUTTON_START_SERVER
    ).get_attribute('href')
    assert href_start.endswith(f"/user/{user}")

    # checking stop button is invisible, url is not changed
    #assert is_displayed(browser, HomePageLocators.BUTTON_STOP_SERVER) == False
    assert (
        browser.find_element(*HomePageLocators.BUTTON_STOP_SERVER).get_attribute(
            'style'
        )
        == 'display:none;'
    )
    assert '/hub/home' in browser.current_url()"""
    """Start server"""
    """
    click(browser, HomePageLocators.BUTTON_START_SERVER)
    if f'/user/{user}' not in browser.current_url:
        await webdriver_wait(browser, EC.url_to_be(browser.current_url))
    else:
        pass
    assert f'/user/{user}/' in browser.current_url()
    """


async def test_user_logout_home_page(app, browser):

    await open_home_page(app, browser, user="test_user", pass_w="test_user")
    if is_displayed(browser, HomePageLocators.BUTTON_LOGOUT) == False:
        await webdriver_wait(
            browser, EC.presence_of_element_located(HomePageLocators.BUTTON_LOGOUT)
        )
    else:
        click(browser, HomePageLocators.BUTTON_LOGOUT)
    await webdriver_wait(browser, EC.url_changes(browser.current_url))
    # checking url changing to login url and login form is displayed
    assert 'hub/login' in browser.current_url
    assert is_displayed(browser, LoginPageLocators.FORM_LOGIN) == True
    elements_home_bar = browser.find_elements(*HomePageLocators.LINK_HOME_BAR)
    assert len(elements_home_bar) == 1  # including 1 element
    for element_home_bar in elements_home_bar:
        assert element_home_bar.get_attribute('href').endswith('hub/')


# TOKEN PAGE
async def open_token_page(app, browser, user="test_user", pass_w="test_user"):

    url = url_path_join(public_host(app), app.hub.base_url, "/login?next=/hub/token")
    await in_thread(browser.get, url)
    redirected_url = url_path_join(public_host(app), app.base_url, '/hub/token')
    await login(browser, user, pass_w)
    await in_thread(browser.get, redirected_url)
    # verify home page is opened and  contains username
    if '/hub/token' not in browser.current_url:
        await webdriver_wait(browser, EC.url_to_be(redirected_url))
    else:
        pass
    assert browser.current_url == redirected_url


async def test_elements_of_token_page(app, browser):
    await open_token_page(app, browser, user="test_user123", pass_w="test_user123")
    user = "test_user123"

    """to be done - add checking of HOME_BAR"""
    ### Request token form ###
    assert is_displayed(browser, TokenPageLocators.BUTTON_API_REQ) == True
    time.sleep(20)
    button_api_req_color = Color.from_string(
        browser.find_element(*TokenPageLocators.BUTTON_API_REQ).value_of_css_property(
            'background-color'
        )
    )
    button_api_req_text_color = Color.from_string(
        browser.find_element(*TokenPageLocators.BUTTON_API_REQ).value_of_css_property(
            'color'
        )
    )
    button_api_req_text = browser.find_element(
        *TokenPageLocators.BUTTON_API_REQ
    ).get_attribute('innerHTML')
    button_api_req_text_size = browser.find_element(
        *TokenPageLocators.BUTTON_API_REQ
    ).value_of_css_property('font-size')
    button_api_req_text_font = browser.find_element(
        *TokenPageLocators.BUTTON_API_REQ
    ).value_of_css_property('font-family')
    # print(button_api_req_text_size, button_api_req_text_font)
    # print(browser.find_element(*TokenPageLocators.BUTTON_API_REQ).rect) #buttons size and coordinates
    assert button_api_req_color.hex == '#f37524'
    assert button_api_req_text_color.hex == '#ffffff'
    assert button_api_req_text.strip() == TokenPageLocators.BUTTON_API_REQ_NAME

    assert is_displayed(browser, TokenPageLocators.INPUT_TOKEN) == True
    # verify that Note field is editable
    send_text(browser, TokenPageLocators.INPUT_TOKEN, "test_text")
    assert (
        browser.find_element(*TokenPageLocators.INPUT_TOKEN).get_attribute('value')
        == "test_text"
    )

    assert is_displayed(browser, TokenPageLocators.LIST_EXP_TOKEN_FIELD) == True

    # checking that token expiration = "Never" selected
    options = browser.find_elements(*TokenPageLocators.LIST_EXP_TOKEN_OPT)
    Dict_opt_list = {}
    for option in options:
        Dict_opt_list[option.text] = option.get_attribute('value')
        is_selected = option.is_selected()
        option.text
    print(Dict_opt_list)
    assert is_selected == True
    assert option.text == "Never"
    # verify that dropdown list contains expected items
    assert Dict_opt_list == TokenPageLocators.LIST_EXP_TOKEN_OPT_DICT

    ### No API Tokens table ###

    """TBD"""
    # assert buttonAPI == True
    # assert token_note == True
    # assert token_dropdown == True


async def test_request_token(app, browser, user, pass_w):
    await login(app, browser, user, pass_w)
    cookies = await app.login_user(user)
    await get_page("token", app, cookies=cookies)

    ######################################################################
    ### API Tokens table ###
    table = browser.find_element(*TokenPageLocators.TABLE_API)
    head = table.find_element(*TokenPageLocators.TABLE_API_HEAD)
    body = table.find_element(*TokenPageLocators.TABLE_API_BODY)
    rows_head = head.find_elements(*TokenPageLocators.TABLE_API_ROWS)
    rows_body = body.find_elements(*TokenPageLocators.TABLE_API_ROWS_BY_CLASS)
    assert is_displayed(browser, TokenPageLocators.TABLE_API) == True
    assert is_displayed(browser, TokenPageLocators.TABLE_API_HEAD) == True
    assert is_displayed(browser, TokenPageLocators.TABLE_API_BODY) == True
    assert int(len(rows_head)) == 1
    assert int(len(rows_body)) == 1

    List_rows_head = []
    List_col_head = []
    # verify head of table rows
    for row_head in rows_head:
        i = row_head.text
        List_rows_head.append(i)
        columns_head = rows_head[0].find_elements(*TokenPageLocators.TABLE_API_COLUMNS)
        for column_head in columns_head:
            j = column_head.text
            List_col_head.append(j)
    print("List_col_head")
    print(List_col_head)
    assert List_col_head == TokenPageLocators.TABLE_API_HEAD_LIST

    # verify body of table
    Dict_body_rows = {}
    Dict_body_columns = {}
    for i in range(len(rows_body)):
        Dict_body_rows[i] = rows_body[i].text
        columns_body = rows_body[i].find_elements(*TokenPageLocators.TABLE_API_COLUMNS)
        for j in range(len(columns_body)):
            Dict_body_columns[j] = columns_body[j].text
    print("Dict_body_rows:")
    print(Dict_body_rows)
    print("Dict_body_columns:")
    print(Dict_body_columns)
    assert is_displayed(browser, TokenPageLocators.TABLE_API_COLUMNS) == True
    assert int(len(columns_head)) == 4
    assert int(len(columns_body)) == 5
    assert Dict_body_columns.get(0) == "Server at " + (
        ujoin(app.base_url, f"/user/{user}/")
    )
    assert Dict_body_columns.get(3) == "Never"
    buttons = rows_body.find_elements(*TokenPageLocators.BUTTON_REVOKE)
    print(len(buttons))
    # button = rows_body.find_element(By.XPATH, '/html/body/div[1]/div[3]/table/tbody/tr[1]/td[5]/button')
    # print(button.text)

    """for button in buttons:
        button = button.text
        button.get_attribute('text')"""

    # print(button[0].get_attribute('text'))
    # = button.find_element(*TokenPageLocators.BUTTON_REVOKE)
    # assert text in Dict_body_columns.get(4)

    # at first time before getting the API token"""
    time.sleep(5)
    # assert is_displayed(browser,TokenPageLocators.PANEL_AREA)== False
    # assert browser.find_element(*TokenPageLocators.PANEL_AREA).get_attribute('style') !="display: none;"


async def test_user_logout_token_page(app, browser):

    await open_token_page(app, browser, user="test_user", pass_w="test_user")

    if is_displayed(browser, HomePageLocators.BUTTON_LOGOUT) == False:
        await webdriver_wait(
            browser, EC.presence_of_element_located(HomePageLocators.BUTTON_LOGOUT)
        )
    else:
        click(browser, HomePageLocators.BUTTON_LOGOUT)
    await webdriver_wait(browser, EC.url_changes(browser.current_url))
    # checking url changing to login url and login form is displayed
    assert 'hub/login' in browser.current_url
    assert is_displayed(browser, LoginPageLocators.FORM_LOGIN) == True
    elements_home_bar = browser.find_elements(*HomePageLocators.LINK_HOME_BAR)
    assert len(elements_home_bar) == 1  # including 1 element
    for element_home_bar in elements_home_bar:
        assert element_home_bar.get_attribute('href').endswith('hub/')
