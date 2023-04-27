"""Tests for the Selenium WebDriver"""

import asyncio
import json
from functools import partial
from urllib.parse import parse_qs, urlparse

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tornado.escape import url_escape
from tornado.httputil import url_concat

from jupyterhub import scopes
from jupyterhub.tests.selenium.locators import BarLocators, LoginPageLocators
from jupyterhub.utils import exponential_backoff

from ... import orm, roles
from ...utils import url_path_join
from ..utils import public_host, public_url, ujoin

pytestmark = pytest.mark.browser


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


# HOME PAGE


async def wait_for_ready(browser):
    """Wait for javascript on the page to finish loading

    otherwise, click events may not do anything
    """
    if "/hub/admin" in browser.current_url:
        await webdriver_wait(
            browser,
            lambda browser: is_displayed(
                browser,
                (By.XPATH, '//div[@class="resets"]/div[@data-testid="container"]'),
            ),
        )
    else:
        await webdriver_wait(
            browser,
            lambda driver: driver.execute_script(
                "return window._jupyterhub_page_loaded;"
            ),
        )


async def open_home_page(app, browser, user):
    """function to open the home page"""

    home_page = url_escape(app.base_url) + "hub/home"
    await open_url(app, browser, path="/login?next=" + home_page)
    await login(browser, user.name, pass_w=str(user.name))
    await webdriver_wait(browser, EC.url_contains('/hub/home'))
    # wait for javascript to finish loading
    await wait_for_ready(browser)


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
    expected_redirect_url = url_path_join(
        app.base_url + f"services/{service.name}/oauth_callback"
    )
    # decode the URL
    query_params = parse_qs(urlparse(browser.current_url).query)
    query_params = parse_qs(urlparse(query_params['next'][0]).query)

    assert f"service-{expected_client_id}" == query_params['client_id'][0]
    assert expected_redirect_url == query_params['redirect_uri'][0]

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
    await wait_for_ready(browser)


def create_list_of_users(create_user_with_scopes, n):
    return [create_user_with_scopes("self") for i in range(n)]


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
    """interaction with paging buttons, where number 1 = previous and number 2 = next"""
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


async def test_start_stop_server_on_admin_page(
    app,
    browser,
    admin_user,
    create_user_with_scopes,
):
    async def click_start_server(browser, username):
        start_button_xpath = f'//a[contains(@href, "spawn/{username}")]/preceding-sibling::button[contains(@class, "start-button")]'
        await click(browser, (By.XPATH, start_button_xpath))
        start_btn = browser.find_element(By.XPATH, start_button_xpath)
        await wait_for_ready(browser)
        await webdriver_wait(browser, EC.staleness_of(start_btn))

    async def click_spawn_page(browser, app, username):
        spawn_button_xpath = f'//a[contains(@href, "spawn/{username}")]/button[contains(@class, "secondary")]'
        await click(browser, (By.XPATH, spawn_button_xpath))
        while (
            not app.users[1].spawner.ready
            and f"/hub/spawn-pending/{username}" in browser.current_url
        ):
            await webdriver_wait(browser, EC.url_contains(f"/user/{username}/"))

    async def click_access_server(browser, username):
        access_btn_xpath = f'//a[contains(@href, "user/{username}")]/button[contains(@class, "primary")]'
        await click(browser, (By.XPATH, access_btn_xpath))
        await webdriver_wait(browser, EC.url_contains(f"/user/{username}/"))

    async def click_stop_button(browser, username):
        stop_btn_xpath = f'//a[contains(@href, "user/{username}")]/preceding-sibling::button[contains(@class, "stop-button")]'
        stop_btn = browser.find_element(By.XPATH, stop_btn_xpath)
        await click(browser, (By.XPATH, stop_btn_xpath))
        await webdriver_wait(browser, EC.staleness_of(stop_btn))

    user1, user2 = create_list_of_users(create_user_with_scopes, 2)
    await open_admin_page(app, browser, admin_user)

    user_name_elements = browser.find_elements(
        By.XPATH, '//td[@data-testid="user-row-name"]'
    )
    assert {user1.name, user2.name}.issubset({e.text for e in user_name_elements})

    spawn_page_btns = browser.find_elements(
        By.XPATH,
        '//*[@data-testid="user-row-server-activity"]//a[contains(@href, "spawn/")]',
    )

    for spawn_page_btn, name_element in zip(spawn_page_btns, user_name_elements):
        link = spawn_page_btn.get_attribute('href')
        assert f"/spawn/{name_element.text}" in link

    # click on Start button
    await click_start_server(browser, user1.name)
    class_names = ["stop-button", "primary", "start-button", "secondary"]
    btns = {
        class_name: get_users_buttons(browser, class_name) for class_name in class_names
    }
    assert len(btns["stop-button"]) == 1

    # click on Spawn page button
    await click_spawn_page(browser, app, user2.name)
    assert f"/user/{user2.name}/" in browser.current_url

    # open the Admin page
    await open_url(app, browser, "/admin")
    # wait for javascript to finish loading
    await wait_for_ready(browser)
    assert "/hub/admin" in browser.current_url
    btns = {
        class_name: get_users_buttons(browser, class_name) for class_name in class_names
    }
    assert len(btns["stop-button"]) == len(btns["primary"]) == 2

    # click on the Access button
    await click_access_server(browser, user1.name)

    # go back to the admin page
    await open_url(app, browser, "/admin")
    await wait_for_ready(browser)

    # click on Stop button for both users
    for username in (user1.name, user2.name):
        await click_stop_button(browser, username)
    btns = {
        class_name: get_users_buttons(browser, class_name) for class_name in class_names
    }
    assert len(btns["stop-button"]) == 0
    assert len(btns["primary"]) == 0
