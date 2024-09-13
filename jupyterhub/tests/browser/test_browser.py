"""Tests for the Playwright Python"""

import asyncio
import json
import pprint
import re
from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.async_api import expect
from tornado.escape import url_escape
from tornado.httputil import url_concat

from jupyterhub import orm, roles, scopes
from jupyterhub.tests.test_named_servers import named_servers  # noqa
from jupyterhub.tests.utils import async_requests, public_host, public_url, ujoin
from jupyterhub.utils import url_escape_path, url_path_join

pytestmark = pytest.mark.browser


async def login(browser, username, password=None):
    """filling the login form by user and pass_w parameters and initiate the login"""
    if password is None:
        password = username

    await browser.get_by_label("Username:").click()
    await browser.get_by_label("Username:").fill(username)
    await browser.get_by_label("Password:").click()
    await browser.get_by_label("Password:").fill(password)
    await browser.get_by_role("button", name="Sign in").click()


async def login_home(browser, app, username):
    """Visit login page, login, go home

    A good way to start a session
    """
    login_url = url_concat(
        url_path_join(public_url(app), "hub/login"),
        {"next": ujoin(app.hub.base_url, "home")},
    )
    await browser.goto(login_url)
    async with browser.expect_navigation(url=re.compile(".*/hub/home")):
        await login(browser, username)


async def test_open_login_page(app, browser):
    login_url = url_path_join(public_host(app), app.hub.base_url, "login")
    await browser.goto(login_url)
    await expect(browser).to_have_url(re.compile(r".*/login"))
    await expect(browser).to_have_title("JupyterHub")
    form = browser.locator('//*[@id="login-main"]/form')
    await expect(form).to_be_visible()
    await expect(form.locator('//h1')).to_have_text("Sign in")


async def test_submit_login_form(app, browser, user_special_chars):
    user = user_special_chars.user
    login_url = url_path_join(public_host(app), app.hub.base_url, "login")
    await browser.goto(login_url)
    await login(browser, user.name, password=user.name)
    expected_url = public_url(app, user)
    await expect(browser).to_have_url(expected_url)


@pytest.mark.parametrize(
    'url, params, redirected_url, form_action',
    [
        (
            # spawn?param=value
            # will encode given parameters for an unauthenticated URL in the next url
            # the next parameter will contain the app base URL (replaces BASE_URL in tests)
            'spawn',
            {'param': 'value'},
            '/hub/login?next={{BASE_URL}}hub%2Fspawn%3Fparam%3Dvalue',
            '/hub/login?next={{BASE_URL}}hub%2Fspawn%3Fparam%3Dvalue',
        ),
        (
            # login?param=fromlogin&next=encoded(/hub/spawn?param=value)
            # will drop parameters given to the login page, passing only the next url
            'login',
            {'param': 'fromlogin', 'next': '/hub/spawn?param=value'},
            '/hub/login?param=fromlogin&next={{BASE_URL}}hub%2Fspawn%3Fparam%3Dvalue',
            '/hub/login?next={{BASE_URL}}hub%2Fspawn%3Fparam%3Dvalue',
        ),
        (
            # login?param=value&anotherparam=anothervalue
            # will drop parameters given to the login page, and use an empty next url
            'login',
            {'param': 'value', 'anotherparam': 'anothervalue'},
            '/hub/login?param=value&anotherparam=anothervalue',
            '/hub/login?next=',
        ),
        (
            # login
            # simplest case, accessing the login URL, gives an empty next url
            'login',
            {},
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
    user_special_chars,
):
    user = user_special_chars.user
    login_url = url_path_join(public_host(app), app.hub.base_url, url)
    await browser.goto(login_url)
    if params.get("next"):
        params["next"] = url_path_join(app.base_url, params["next"])
    url_new = url_path_join(public_host(app), app.hub.base_url, url_concat(url, params))
    print(url_new)
    await browser.goto(url_new)
    redirected_url = redirected_url.replace(
        '{{BASE_URL}}', url_escape_path(app.base_url)
    )
    form_action = form_action.replace('{{BASE_URL}}', url_escape(app.base_url))

    form = browser.locator('//*[@id="login-main"]/form')

    # verify title / url
    await expect(browser).to_have_title("JupyterHub")
    f_string = re.escape(f"{form_action}")
    await expect(form).to_have_attribute('action', re.compile('.*' + f_string))

    # login in with params
    await login(browser, user.name, password=user.name)
    # verify next url + params
    if url_escape(app.base_url) in form_action:
        await expect(browser).to_have_url(re.compile(".*param=value"))
    elif "next=%2Fhub" in form_action:
        escaped_string = re.escape('spawn?param=value')
        pattern = re.compile('.*' + escaped_string)
        await expect(browser).to_have_url(re.compile(pattern))
        await expect(browser).not_to_have_url(re.compile(".*/user/.*"))
    else:
        await expect(browser).to_have_url(
            re.compile(".*/user/" + f"{user_special_chars.urlname}/")
        )


@pytest.mark.parametrize(
    "username, pass_w",
    [
        (" ", ""),
        ("user", ""),
        (" ", "password"),
        ("user", "password"),
    ],
)
async def test_login_with_invalid_credentials(app, browser, username, pass_w):
    login_url = url_path_join(public_host(app), app.hub.base_url, "login")
    await browser.goto(login_url)
    await login(browser, username, pass_w)
    locator = browser.locator("p.login_error")
    expected_error_message = "Invalid username or password"
    # verify error message displayed and user stays on login page
    await expect(locator).to_be_visible()
    await expect(locator).to_contain_text(expected_error_message)
    await expect(browser).to_have_url(re.compile(".*/hub/login"))


@pytest.mark.parametrize("request_otp", [True, False])
async def test_login_otp(request, app, browser, username, request_otp):
    def _reset():
        app.authenticator.request_otp = False

    request.addfinalizer(_reset)

    app.authenticator.request_otp = request_otp
    login_url = url_concat(
        url_path_join(public_host(app), app.hub.base_url, "login"),
        {"next": ujoin(public_url(app), "/hub/home/")},
    )
    await browser.goto(login_url)
    # check for otp element
    otp_label = browser.locator("label[for=otp_input]")
    otp_input = browser.locator("input#otp_input")
    if not request_otp:
        # request_otp is False, no OTP prompt
        assert await otp_label.count() == 0
        assert await otp_input.count() == 0
        return

    await expect(otp_label).to_be_visible()
    await expect(otp_input).to_be_visible()
    await expect(otp_label).to_have_text(app.authenticator.otp_prompt)

    # fill it out
    await browser.get_by_label("Username:").fill(username)
    await browser.get_by_label("Password:").fill(username)
    await browser.get_by_label("OTP:").fill("otp!")

    # submit form
    with mock.patch(
        "jupyterhub.tests.mocking.mock_authenticate",
        spec=True,
        return_value={"username": username},
    ) as mock_otp_auth:
        await browser.get_by_role("button", name="Sign in").click()
        expected_url = ujoin(public_url(app), "/hub/home/")
        await expect(browser).to_have_url(expected_url)

    # check that OTP was passed
    assert mock_otp_auth.called
    assert mock_otp_auth.call_args.args[0] == username
    assert mock_otp_auth.call_args.args[1] == (username, "otp!")


# SPAWNING


async def open_spawn_pending(app, browser, user_special_chars):
    user = user_special_chars.user
    url = url_path_join(
        public_host(app),
        url_concat(
            url_path_join(app.base_url, "login"),
            {"next": url_path_join(app.base_url, "hub/home")},
        ),
    )
    await browser.goto(url)
    await login(browser, user.name, password=user.name)
    url_spawn = url_path_join(
        public_host(app),
        app.hub.base_url,
        '/spawn-pending/' + user_special_chars.urlname,
    )
    await browser.goto(url_spawn)
    await expect(browser).to_have_url(url_spawn)


async def test_spawn_pending_server_not_started(
    app, browser, no_patience, user_special_chars, slow_spawn
):
    user = user_special_chars.user
    # first request, no spawn is pending
    # spawn-pending shows button linking to spawn
    await open_spawn_pending(app, browser, user_special_chars)
    # on the page verify the button and expected information
    expected_heading = "Server not running"
    heading = browser.locator('//div[@class="text-center"]').get_by_role("heading")
    await expect(heading).to_have_text(expected_heading)
    await expect(heading).to_be_visible()
    expected_button_name = "Launch Server"
    launch_btn = browser.locator('//div[@class="text-center"]').get_by_role("button")
    await expect(launch_btn).to_have_text(expected_button_name)
    await expect(launch_btn).to_have_id("start")
    await expect(launch_btn).to_be_enabled()
    await expect(launch_btn).to_have_count(1)
    f_string = re.escape(f"/hub/spawn/{user_special_chars.urlname}")
    await expect(launch_btn).to_have_attribute('href', re.compile('.*' + f_string))


async def test_spawn_pending_progress(
    app, browser, no_patience, user_special_chars, slow_spawn
):
    """verify that the server process messages are showing up to the user
    when the server is going to start up"""

    user = user_special_chars.user
    urlname = user_special_chars.urlname
    # visit the spawn-pending page
    await open_spawn_pending(app, browser, user_special_chars)
    launch_btn = browser.locator("//div[@class='text-center']").get_by_role(
        "button", name="Launch Server"
    )
    await expect(launch_btn).to_be_enabled()

    # begin starting the server
    async with browser.expect_navigation(
        url=re.compile(".*/spawn-pending/" + f"{urlname}")
    ):
        await launch_btn.click()
    # wait for progress message to appear
    progress = browser.locator("#progress-message")
    progress_message = await progress.text_content()
    async with browser.expect_navigation(url=re.compile(".*/user/" + f"{urlname}/")):
        # wait for log messages to appear
        expected_messages = [
            "Server requested",
            "Spawning server...",
            f"Server ready at {app.base_url}user/{urlname}/",
        ]
        while not user.spawner.ready:
            logs_list = [
                await log.text_content()
                for log in await browser.locator("div.progress-log-event").all()
            ]
            if progress_message:
                assert progress_message in expected_messages
            # race condition: progress_message _should_
            # be the last log message, but it _may_ be the next one
            if logs_list:
                assert progress_message
            assert logs_list == expected_messages[: len(logs_list)]
    await expect(browser).to_have_url(re.compile(".*/user/" + f"{urlname}/"))
    assert user.spawner.ready


async def test_spawn_pending_server_ready(app, browser, user_special_chars):
    """verify that after a successful launch server via the spawn-pending page
    the user should see two buttons on the home page"""

    user = user_special_chars.user
    await open_spawn_pending(app, browser, user_special_chars)
    launch_btn = browser.get_by_role("button", name="Launch Server")
    await launch_btn.click()
    await browser.wait_for_selector("button", state="detached")
    home_page = url_path_join(public_host(app), ujoin(app.base_url, "hub/home"))
    await browser.goto(home_page)
    await browser.wait_for_load_state("domcontentloaded")
    # checking that server is running and two butons present on the home page
    stop_start_btns = browser.locator('//div[@class="text-center"]').get_by_role(
        "button"
    )
    expected_btns_name = ["Stop My Server", "My Server"]
    await expect(stop_start_btns).to_have_count(2)
    await expect(stop_start_btns).to_have_text(expected_btns_name)
    await expect(stop_start_btns.nth(0)).to_have_id("stop")
    await expect(stop_start_btns.nth(1)).to_have_id("start")


# HOME PAGE


async def open_home_page(app, browser, user):
    """function to open the home page"""

    home_page = url_escape(app.base_url) + "hub/home"
    url = url_path_join(public_host(app), app.hub.base_url, "/login?next=" + home_page)
    await browser.goto(url)
    await login(browser, user.name, password=str(user.name))
    await expect(browser).to_have_url(re.compile(".*/hub/home"))


async def test_home_nav_collapse(app, browser, user_special_chars):
    user = user_special_chars.user
    await open_home_page(app, browser, user)
    nav = browser.locator(".navbar")
    navbar_collapse = nav.locator(".navbar-collapse")
    logo = nav.locator("#jupyterhub-logo")
    home = nav.get_by_text("Home")
    logout_name = nav.get_by_text(user.name)
    logout_btn = nav.get_by_text("Logout")
    toggler = nav.locator(".navbar-toggler")

    await expect(nav).to_be_visible()

    await browser.set_viewport_size({"width": 640, "height": 480})
    # links visible, nav items visible, collapse not visible
    await expect(logo).to_be_visible()
    await expect(home).to_be_visible()
    await expect(logout_name).to_be_visible()
    await expect(logout_btn).to_be_visible()
    await expect(toggler).not_to_be_visible()

    # below small breakpoint (576px)
    await browser.set_viewport_size({"width": 500, "height": 480})
    # logo visible, links and logout not visible, toggler visible
    await expect(logo).to_be_visible()
    await expect(home).not_to_be_visible()
    await expect(logout_name).not_to_be_visible()
    await expect(logout_btn).not_to_be_visible()
    await expect(toggler).to_be_visible()

    # click toggler, links should be visible
    await toggler.click()
    # wait for expand to finish
    # expand animates through `collapse -> collapsing -> collapse show`
    await expect(navbar_collapse).to_have_class(re.compile(r"\bshow\b"))
    await expect(home).to_be_visible()
    await expect(logout_name).to_be_visible()
    await expect(logout_btn).to_be_visible()
    await expect(toggler).to_be_visible()
    # wait for expand animation
    # click toggler again, links should hide
    # need to wait for expand to complete
    await toggler.click()
    await expect(navbar_collapse).not_to_have_class(re.compile(r"\bshow\b"))
    await expect(home).not_to_be_visible()
    await expect(logout_name).not_to_be_visible()
    await expect(logout_btn).not_to_be_visible()
    await expect(toggler).to_be_visible()

    # resize, should re-show
    await browser.set_viewport_size({"width": 640, "height": 480})
    await expect(logo).to_be_visible()
    await expect(home).to_be_visible()
    await expect(logout_name).to_be_visible()
    await expect(logout_btn).to_be_visible()
    await expect(toggler).not_to_be_visible()


async def test_start_button_server_not_started(app, browser, user_special_chars):
    """verify that when server is not started one button is available,
    after starting 2 buttons are available"""
    user = user_special_chars.user
    urlname = user_special_chars.urlname
    await open_home_page(app, browser, user)
    # checking that only one button is presented
    start_stop_btns = browser.locator('//div[@class="text-center"]').get_by_role(
        "button"
    )
    expected_btn_name = "Start My Server"
    await expect(start_stop_btns).to_be_enabled()
    await expect(start_stop_btns).to_have_count(1)
    await expect(start_stop_btns).to_have_text(expected_btn_name)
    f_string = re.escape(f"/hub/spawn/{urlname}")
    await expect(start_stop_btns).to_have_attribute('href', re.compile('.*' + f_string))
    async with browser.expect_navigation(url=re.compile(".*/user/" + f"{urlname}/")):
        # Start server via clicking on the Start button
        await start_stop_btns.click()
    # return to Home page
    next_url = url_path_join(public_host(app), app.base_url, '/hub/home')
    await browser.goto(next_url)
    # verify that 2 buttons are displayed on the home page
    await expect(start_stop_btns).to_have_count(2)
    expected_btns_names = ["Stop My Server", "My Server"]
    await expect(start_stop_btns).to_have_text(expected_btns_names)
    [
        await expect(start_stop_btn).to_be_enabled()
        for start_stop_btn in await start_stop_btns.all()
    ]
    f_string = re.escape(f"/user/{urlname}")
    await expect(start_stop_btns.nth(1)).to_have_attribute(
        'href', re.compile('.*' + f_string)
    )
    await expect(start_stop_btns.nth(0)).to_have_id("stop")
    await expect(start_stop_btns.nth(1)).to_have_id("start")


async def test_stop_button(app, browser, user_special_chars):
    """verify that the stop button after stopping a server is not shown
    the start button is displayed with new name"""

    user = user_special_chars.user
    await open_home_page(app, browser, user)
    # checking that only one button is presented
    start_stop_btns = browser.locator('//div[@class="text-center"]').get_by_role(
        "button"
    )
    async with browser.expect_navigation(
        url=re.compile(".*/user/" + re.escape(user_special_chars.urlname) + "/")
    ):
        # Start server via clicking on the Start button
        await start_stop_btns.click()
    assert user.spawner.ready
    next_url = url_path_join(public_host(app), app.base_url, '/hub/home')
    await browser.goto(next_url)
    await expect(start_stop_btns.nth(0)).to_have_id("stop")
    # Stop server via clicking on the "Stop My Server"
    await start_stop_btns.nth(0).click()
    await expect(start_stop_btns).to_have_count(1)
    f_string = re.escape(f"/hub/spawn/{user.name}")
    await expect(start_stop_btns).to_have_attribute('href', re.compile('.*' + f_string))
    expected_btn_name = "Start My Server"
    await expect(start_stop_btns).to_have_text(expected_btn_name)
    await expect(start_stop_btns).to_have_id("start")


# TOKEN PAGE


async def open_token_page(app, browser, user):
    """function to open the token page"""

    token_page = url_escape(app.base_url) + "hub/token"
    url = url_path_join(public_host(app), app.hub.base_url, "/login?next=" + token_page)
    await browser.goto(url)
    await login(browser, user.name, password=str(user.name))
    await expect(browser).to_have_url(re.compile(".*/hub/token"))


@pytest.mark.parametrize(
    "expires_in_max, expected_options",
    [
        pytest.param(
            None,
            [
                ('1 Hour', '3600'),
                ('1 Day', '86400'),
                ('1 Week', '604800'),
                ('1 Month', '2592000'),
                ('1 Year', '31536000'),
                ('Never', ''),
            ],
            id="default",
        ),
        pytest.param(
            86400,
            [
                ('1 Hour', '3600'),
                ('1 Day', '86400'),
            ],
            id="1day",
        ),
        pytest.param(
            3600 * 36,
            [
                ('1 Hour', '3600'),
                ('1 Day', '86400'),
                ('Max (36 hours)', ''),
            ],
            id="36hours",
        ),
        pytest.param(
            86400 * 10,
            [
                ('1 Hour', '3600'),
                ('1 Day', '86400'),
                ('1 Week', '604800'),
                ('Max (10 days)', ''),
            ],
            id="10days",
        ),
    ],
)
async def test_token_form_expires_in(
    app, browser, user_special_chars, expires_in_max, expected_options
):
    with mock.patch.dict(
        app.tornado_settings, {"token_expires_in_max_seconds": expires_in_max}
    ):
        await open_token_page(app, browser, user_special_chars.user)
    # check the list of tokens duration
    dropdown = browser.locator('#token-expiration-seconds')
    options = await dropdown.locator('option').all()
    actual_values = [
        (await option.text_content(), await option.get_attribute('value'))
        for option in options
    ]
    assert actual_values == expected_options
    # get the value of the 'selected' attribute of the currently selected option
    selected_value = dropdown.locator('option[selected]')
    await expect(selected_value).to_have_text(expected_options[-1][0])


async def test_token_request_form_and_panel(app, browser, user_special_chars):
    """verify elements of the request token form"""

    await open_token_page(app, browser, user_special_chars.user)
    request_btn = browser.locator('//button[@type="submit"]')
    expected_btn_name = 'Request new API token'
    # check if the request token button is enabled
    # check the buttons name
    await expect(request_btn).to_be_enabled()
    await expect(request_btn).to_have_text(expected_btn_name)
    # check that the field is enabled and editable and empty by default
    field_note = browser.get_by_label('Note')
    await expect(field_note).to_be_editable()
    await expect(field_note).to_be_enabled()
    await expect(field_note).to_be_empty()

    # check scopes field
    scopes_input = browser.get_by_label("Permissions")
    await expect(scopes_input).to_be_editable()
    await expect(scopes_input).to_be_enabled()
    await expect(scopes_input).to_be_empty()

    # verify that "Your new API Token" panel shows up with the new API token
    await request_btn.click()
    await browser.wait_for_load_state("load")
    expected_panel_token_heading = "Your new API Token"
    token_area = browser.locator('#token-area')
    await expect(token_area).to_be_visible()
    token_area_heading = token_area.locator('div.card-header')
    await expect(token_area_heading).to_have_text(expected_panel_token_heading)
    token_result = browser.locator('#token-result')
    await expect(token_result).not_to_be_empty()
    await expect(token_result).to_be_visible()
    # verify that "Your new API Token" panel is hidden after refresh the page
    await browser.reload(wait_until="load")
    await expect(token_area).to_be_hidden()
    api_token_table_area = browser.locator("div#api-tokens-section")
    await expect(api_token_table_area.get_by_role("table")).to_be_visible()
    expected_table_name = "API Tokens"
    await expect(api_token_table_area.get_by_role("heading")).to_have_text(
        expected_table_name
    )


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
async def test_request_token_expiration(
    app, browser, token_opt, note, user_special_chars
):
    """verify request token with the different options"""

    user = user_special_chars.user
    urlname = user_special_chars.urlname
    if token_opt == "server_up":
        # open the home page
        await open_home_page(app, browser, user)
        # start server via clicking on the Start button
        async with browser.expect_navigation(url=f"**/user/{urlname}/"):
            await browser.locator("#start").click()
        token_page = url_path_join(public_host(app), app.base_url, '/hub/token')
        await browser.goto(token_page)
    else:
        # open the token page
        await open_token_page(app, browser, user)
        if token_opt not in ["Never", "server_up"]:
            await browser.get_by_label('Token expires').select_option(token_opt)
        if note:
            note_field = browser.get_by_role("textbox").first
            await note_field.fill(note)
        # click on Request token button
        request_button = browser.locator('//button[@type="submit"]')
        await request_button.click()
        # wait for token response to show up on the page
        await browser.wait_for_load_state("load")
        token_result = browser.locator("#token-result")
        await expect(token_result).to_be_visible()
        # reload the page
        await browser.reload(wait_until="load")
    # API Tokens table: verify that elements are displayed
    api_token_table_area = browser.locator("div#api-tokens-section")
    await expect(api_token_table_area.get_by_role("table")).to_be_visible()
    await expect(api_token_table_area.locator("tr.token-row")).to_have_count(1)

    # getting values from DB to compare with values on UI
    assert len(user.api_tokens) == 1
    orm_token = user.api_tokens[-1]

    if token_opt == "server_up":
        expected_note = "Server at " + ujoin(app.base_url, f"/user/{urlname}/")
    elif note:
        expected_note = note
    else:
        expected_note = "Requested via token page"
    assert orm_token.note == expected_note

    note_on_page = (
        await api_token_table_area.locator("tr.token-row")
        .get_by_role("cell")
        .nth(0)
        .text_content()
    )

    assert note_on_page == expected_note

    last_used_text = (
        await api_token_table_area.locator("tr.token-row")
        .get_by_role("cell")
        .nth(2)
        .text_content()
    )
    assert last_used_text == "Never"

    expires_at_text = (
        await api_token_table_area.locator("tr.token-row")
        .get_by_role("cell")
        .nth(4)
        .text_content()
    )

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
    revoke_btn = (
        api_token_table_area.locator("tr.token-row").get_by_role("button").nth(0)
    )
    await expect(revoke_btn).to_be_visible()
    await expect(revoke_btn).to_have_text("revoke")


@pytest.mark.parametrize(
    "permissions_str, granted",
    [
        ("", {"inherit"}),
        ("inherit", {"inherit"}),
        ("read:users!user, ", {"read:users!user"}),
        (
            "read:users!user, access:servers!user",
            {"read:users!user", "access:servers!user"},
        ),
        (
            "read:users:name!user access:servers!user ,,   read:servers!user",
            {"read:users:name!user", "access:servers!user", "read:servers!user"},
        ),
        # errors
        ("nosuchscope", "does not exist"),
        ("inherit, nosuchscope", "does not exist"),
        ("admin:users", "Not assigning requested scopes"),
    ],
)
async def test_request_token_permissions(
    app, browser, permissions_str, granted, user_special_chars
):
    """verify request token with the different options"""

    user = user_special_chars.user
    # open the token page
    await open_token_page(app, browser, user)
    scopes_input = browser.get_by_label("Permissions")
    await scopes_input.fill(permissions_str)
    request_button = browser.locator('//button[@type="submit"]')
    await request_button.click()

    if isinstance(granted, str):
        expected_error = granted
        granted = False

    if not granted:
        error_dialog = browser.locator("#error-dialog")
        await expect(error_dialog).to_be_visible()
        error_message = await error_dialog.locator(".modal-body").text_content()
        assert "API request failed (400)" in error_message
        assert expected_error in error_message
        await error_dialog.locator("button[aria-label='Close']").click()
        await expect(error_dialog).not_to_be_visible()
        return

    await browser.reload(wait_until="load")

    # API Tokens table: verify that elements are displayed
    api_token_table_area = browser.locator("div#api-tokens-section")
    await expect(api_token_table_area.get_by_role("table")).to_be_visible()
    await expect(api_token_table_area.locator("tr.token-row")).to_have_count(1)

    # getting values from DB to compare with values on UI
    assert len(user.api_tokens) == 1
    orm_token = user.api_tokens[-1]
    assert set(orm_token.scopes) == granted

    permissions_on_page = (
        await api_token_table_area.locator("tr.token-row")
        .get_by_role("cell")
        .nth(1)
        .locator('//pre[@class="token-scope"]')
        .all_text_contents()
    )
    # specifically use list to test that entries don't appear twice
    assert sorted(permissions_on_page) == sorted(granted)


@pytest.mark.parametrize(
    "token_type",
    [
        ("server_up"),
        ("request_by_user"),
        ("both"),
    ],
)
async def test_revoke_token(app, browser, token_type, user_special_chars):
    """verify API Tokens table content in case the server is started"""

    user = user_special_chars.user
    # open the home page
    await open_home_page(app, browser, user)
    if token_type == "server_up" or token_type == "both":
        # Start server via clicking on the Start button
        async with browser.expect_navigation(
            url=f"**/user/{user_special_chars.urlname}/"
        ):
            await browser.locator("#start").click()
    # open the token page
    next_url = url_path_join(public_host(app), app.base_url, '/hub/token')
    await browser.goto(next_url)
    await browser.wait_for_load_state("load")
    await expect(browser).to_have_url(re.compile(".*/hub/token"))
    if token_type == "both" or token_type == "request_by_user":
        request_btn = browser.locator('//button[@type="submit"]')
        await request_btn.click()
        # wait for token response to show up on the page
        await browser.wait_for_load_state("load")
        token_result = browser.locator("#token-result")
        await expect(token_result).to_be_visible()
        # reload the page
        await browser.reload(wait_until="load")

    revoke_btns = browser.get_by_role("button", name="revoke")

    # verify that the token revoked from UI and the database
    if token_type in {"server_up", "request_by_user"}:
        await expect(revoke_btns).to_have_count(1)
        await expect(revoke_btns).to_have_count(len(user.api_tokens))
        # click Revoke button
        await revoke_btns.click()
        await expect(browser.locator("tr.token-row")).to_have_count(0)
        await expect(revoke_btns).to_have_count(0)
        await expect(revoke_btns).to_have_count(len(user.api_tokens))

    if token_type == "both":
        # verify that both tokens are revoked from UI and the database
        revoke_btns = browser.get_by_role("button", name="revoke")
        await expect(revoke_btns).to_have_count(2)
        assert len(user.api_tokens) == 2
        for button in await browser.query_selector_all('.revoke-token-btn'):
            await button.click()
            await browser.wait_for_load_state("domcontentloaded")
        await expect(revoke_btns).to_have_count(0)
        await expect(revoke_btns).to_have_count(len(user.api_tokens))


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
async def test_menu_bar(app, browser, page, logged_in, user_special_chars):
    user = user_special_chars.user
    url = url_path_join(
        public_host(app),
        url_concat(
            url_path_join(app.base_url, "/login?next="),
            {"next": url_path_join(app.base_url, page)},
        ),
    )
    await browser.goto(url)
    if page:
        await login(browser, user.name, password=user.name)
    bar_link_elements = browser.locator('//div[@class="container-fluid"]//a')

    if not logged_in:
        await expect(bar_link_elements).to_have_count(1)
    elif "hub/not" in page:
        await expect(bar_link_elements).to_have_count(3)
    else:
        await expect(bar_link_elements).to_have_count(4)
        user_name = browser.get_by_text(f"{user.name}")
        await expect(user_name).to_be_visible()

    # verify the title on the logo
    logo = browser.get_by_role("img")
    await expect(logo).to_have_attribute("title", "Home")
    expected_link_bar_url = ["/hub/", "/hub/home", "/hub/token", "/hub/logout"]
    expected_link_bar_name = ["", "Home", "Token", "Logout"]
    for index in range(await bar_link_elements.count()):
        # verify that links on the topbar work, checking the titles of links
        link = bar_link_elements.nth(index)
        await expect(bar_link_elements.nth(index)).to_have_attribute(
            'href', re.compile('.*' + expected_link_bar_url[index])
        )
        await expect(bar_link_elements.nth(index)).to_have_text(
            expected_link_bar_name[index]
        )
        await link.click()
        if index == 0:
            if not logged_in:
                expected_url = f"hub/login?next={url_escape(app.base_url)}"
                assert expected_url in browser.url
            else:
                await expect(browser).to_have_url(
                    re.compile(f".*/user/{user_special_chars.urlname}/")
                )
                await browser.go_back()
                await expect(browser).to_have_url(re.compile(".*" + page))
        elif index == 3:
            await expect(browser).to_have_url(re.compile(".*/login"))
        else:
            await expect(browser).to_have_url(
                re.compile(".*" + expected_link_bar_url[index])
            )


# LOGOUT


@pytest.mark.parametrize(
    "url",
    [("/hub/home"), ("/hub/token"), ("/hub/spawn")],
)
async def test_user_logout(app, browser, url, user_special_chars):
    user = user_special_chars.user
    if "/hub/home" in url:
        await open_home_page(app, browser, user)
    elif "/hub/token" in url:
        await open_home_page(app, browser, user)
    elif "/hub/spawn" in url:
        await open_spawn_pending(app, browser, user_special_chars)
    logout_btn = browser.get_by_role("button", name="Logout")
    await expect(logout_btn).to_be_enabled()
    await logout_btn.click()
    # checking url changing to login url and login form is displayed
    await expect(browser).to_have_url(re.compile(".*/hub/login"))
    form = browser.locator('//*[@id="login-main"]/form')
    await expect(form).to_be_visible()
    bar_link_elements = browser.locator('//div[@class="container-fluid"]//a')
    await expect(bar_link_elements).to_have_count(1)
    await expect(bar_link_elements).to_have_attribute('href', (re.compile(".*/hub/")))

    # verify that user can login after logout
    await login(browser, user.name, password=user.name)
    await expect(browser).to_have_url(
        re.compile(".*/user/" + f"{user_special_chars.urlname}/")
    )


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
    service_url = url_path_join(public_url(app, service), 'owhoami/?arg=x')
    await browser.goto(service_url)

    if app.subdomain_host:
        expected_redirect_url = url_path_join(
            public_url(app, service), "oauth_callback"
        )
    else:
        expected_redirect_url = url_path_join(service.prefix, "oauth_callback")
    expected_client_id = f"service-{service.name}"

    # decode the URL
    query_params = parse_qs(urlparse(browser.url).query)
    query_params = parse_qs(urlparse(query_params['next'][0]).query)

    # check if the client_id and redirected url in the browser_url
    assert expected_client_id == query_params['client_id'][0]
    assert expected_redirect_url == query_params['redirect_uri'][0]

    # login user
    await login(browser, user.name, password=str(user.name))
    auth_btn = browser.locator('//button[@type="submit"]')
    await expect(auth_btn).to_be_enabled()
    text_permission = browser.get_by_role("paragraph").nth(1)
    await expect(text_permission).to_contain_text(f"JupyterHub service {service.name}")
    await expect(text_permission).to_contain_text(f"oauth URL: {expected_redirect_url}")

    # verify that user can see the service name and oauth URL
    # permissions check
    oauth_form = browser.locator('//form')
    scopes_elements = await oauth_form.locator(
        '//input[@type="hidden" and @name="scopes"]'
    ).all()

    # checking that scopes are invisible on the page
    scope_list_oauth_page = [
        await expect(scopes_element).not_to_be_visible()
        for scopes_element in scopes_elements
    ]
    # checking that all scopes granded to user are presented in POST form (scope_list)
    scope_list_oauth_page = [
        await scopes_element.get_attribute("value")
        for scopes_element in scopes_elements
    ]
    assert all(x in scope_list_oauth_page for x in user_scopes)
    assert f"access:services!service={service.name}" in scope_list_oauth_page

    # checking that user cannot uncheck the checkbox
    check_boxes = await oauth_form.get_by_role('checkbox', name="raw-scopes").all()
    for check_box in check_boxes:
        await expect(check_box).not_to_be_editable()
        await expect(check_box).to_be_disabled()
        await expect(check_box).to_have_value("title", "This authorization is required")

    # checking that appropriete descriptions are displayed depending of scopes
    descriptions = await oauth_form.locator('//span').all()
    desc_list_form = [await description.text_content() for description in descriptions]
    desc_list_form = [" ".join(desc.split()) for desc in desc_list_form]

    # getting descriptions from scopes.py to compare them with descriptions on UI
    scope_descriptions = scopes.describe_raw_scopes(
        user_scopes or ['(no_scope)'], user.name
    )
    desc_list_expected = [
        (
            f"{sd['description']} Applies to {sd['filter']}."
            if sd.get('filter')
            else sd['description']
        )
        for sd in scope_descriptions
    ]
    assert sorted(desc_list_form) == sorted(desc_list_expected)

    # click on the Authorize button
    await auth_btn.click()
    # check that user returned to service page
    await expect(browser).to_have_url(service_url)
    # check the granted permissions by
    # getting the scopes from the service page,
    # which contains the JupyterHub user model
    text = await browser.locator("//body").text_content()
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
        url = url_path_join(
            public_host(app), app.hub.base_url, "/login?next=" + admin_page
        )
        await browser.goto(url)
        await login(browser, user.name, password=str(user.name))
        await expect(browser).to_have_url(re.compile(".*/hub/admin"))
    else:
        # url = url_path_join(public_host(app), app.hub.base_url, "/login?next=" + admin_page)
        await browser.goto(admin_page)
        await expect(browser).to_have_url(re.compile(".*/hub/admin"))
    await browser.wait_for_load_state("networkidle")


def create_list_of_users(create_user_with_scopes, n):
    return [create_user_with_scopes("self") for i in range(n)]


async def test_start_stop_all_servers_on_admin_page(app, browser, admin_user):
    """verifying of working "Start All"/"Stop All" buttons"""

    await open_admin_page(app, browser, admin_user)
    # get total count of users from db
    users_count_db = app.db.query(orm.User).count()
    start_all_btn = browser.get_by_test_id("start-all")
    stop_all_btn = browser.get_by_test_id("stop-all")
    # verify Start All and Stop All buttons are displayed
    await expect(start_all_btn).to_be_enabled()
    await expect(stop_all_btn).to_be_enabled()

    users = browser.get_by_test_id("user-row-name")
    # verify that all servers are not started
    # users´numbers are the same as numbers of the start button and the Spawn page button
    # no Stop server buttons are displayed
    # no access buttons are displayed
    btns_start = browser.get_by_test_id("user-row-server-activity").get_by_role(
        "button", name="Start Server"
    )
    btns_stop = browser.get_by_test_id("user-row-server-activity").get_by_role(
        "button", name="Stop Server"
    )
    btns_spawn = browser.get_by_test_id("user-row-server-activity").get_by_role(
        "button", name="Spawn Page"
    )
    btns_access = browser.get_by_test_id("user-row-server-activity").get_by_role(
        "button", name="Access Server"
    )

    assert (
        await btns_start.count()
        == await btns_spawn.count()
        == await users.count()
        == users_count_db
    )
    assert await btns_stop.count() == await btns_access.count() == 0

    # start all servers via the Start All
    await start_all_btn.click()
    # Start All and Stop All are still displayed
    await expect(start_all_btn).to_be_enabled()
    await expect(stop_all_btn).to_be_enabled()

    for btn_start in await btns_start.all():
        await btn_start.wait_for(state="hidden")
    # users´numbers are the same as numbers of the stop button and the Access button
    # no Start server buttons are displayed
    # no Spawn page buttons are displayed
    assert await btns_start.count() == await btns_spawn.count() == 0
    assert (
        await btns_stop.count()
        == await btns_access.count()
        == await users.count()
        == users_count_db
    )
    # stop all servers via the Stop All
    await stop_all_btn.click()
    for btn_stop in await btns_stop.all():
        await btn_stop.wait_for(state="hidden")
    # verify that all servers are stopped
    # users´numbers are the same as numbers of the start button and the Spawn page button
    # no Stop server buttons are displayed
    # no access buttons are displayed
    await expect(start_all_btn).to_be_enabled()
    await expect(stop_all_btn).to_be_enabled()
    assert (
        await btns_start.count()
        == await btns_spawn.count()
        == await users.count()
        == users_count_db
    )


@pytest.mark.parametrize("added_count_users", [10, 49, 50, 51, 99, 100, 101])
async def test_paging_on_admin_page(
    app, browser, admin_user, added_count_users, create_user_with_scopes
):
    """verifying of displaying number of total users on the admin page and navigation with "Previous"/"Next" buttons"""

    create_list_of_users(create_user_with_scopes, added_count_users)
    await open_admin_page(app, browser, admin_user)
    # get total count of users from db
    users_count_db = app.db.query(orm.User).count()
    # get total count of users from UI page
    displaying = browser.get_by_text("Displaying")
    btn_previous = browser.get_by_role("button", name="Previous")
    btn_next = browser.get_by_role("button", name="Next")
    # verify "Previous"/"Next" button clickability depending on users number on the page
    await expect(displaying).to_have_text(
        re.compile(".*" + f"1-{min(users_count_db, 50)}" + ".*")
    )
    if users_count_db > 50:
        await expect(btn_next).to_be_enabled()
        # click on Next button
        await btn_next.click()
        if users_count_db <= 100:
            await expect(displaying).to_have_text(
                re.compile(".*" + f"51-{users_count_db}" + ".*")
            )
        else:
            await expect(displaying).to_have_text(re.compile(".*" + "51-100" + ".*"))
            await expect(btn_next).to_be_enabled()
        await expect(btn_previous).to_be_enabled()
        # click on Previous button
        await btn_previous.click()
    else:
        await expect(btn_next).to_be_disabled()
        await expect(btn_previous).to_be_disabled()


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
    element_search = browser.locator('//input[@name="user_search"]')
    await element_search.click()
    await element_search.fill(search_value, force=True)
    await browser.wait_for_load_state("networkidle")
    # get the result of the search from db
    users_count_db_filtered = (
        app.db.query(orm.User).filter(orm.User.name.like(f'%{search_value}%')).count()
    )
    # get the result of the search
    filtered_list_on_page = browser.locator('//tr[@class="user-row"]')
    displaying = browser.get_by_text("Displaying")
    if users_count_db_filtered <= 50:
        await expect(filtered_list_on_page).to_have_count(users_count_db_filtered)
        start = 1 if users_count_db_filtered else 0
        await expect(displaying).to_contain_text(
            re.compile(f"{start}-{users_count_db_filtered}")
        )
        # check that users names contain the search value in the filtered list
        for element in await filtered_list_on_page.get_by_test_id(
            "user-row-name"
        ).all():
            await expect(element).to_contain_text(re.compile(f".*{search_value}.*"))
    else:
        await expect(filtered_list_on_page).to_have_count(50)
        await expect(displaying).to_contain_text(re.compile("1-50"))
        # click on Next button to verify that the rest part of filtered list is displayed on the next page
        await browser.get_by_role("button", name="Next").click()
        await browser.wait_for_load_state("networkidle")
        filtered_list_on_next_page = browser.locator('//tr[@class="user-row"]')
        await expect(filtered_list_on_page).to_have_count(users_count_db_filtered - 50)
        for element in await filtered_list_on_next_page.get_by_test_id(
            "user-row-name"
        ).all():
            await expect(element).to_contain_text(re.compile(f".*{search_value}.*"))


async def test_start_stop_server_on_admin_page(
    app,
    browser,
    admin_user,
    create_user_with_scopes,
):
    async def click_start_server(browser, username):
        """start the server for one user via the Start Server button, index = 0 or 1"""
        start_btn_xpath = f'//a[contains(@href, "spawn/{username}")]/preceding-sibling::button[contains(@class, "start-button")]'
        start_btn = browser.locator(start_btn_xpath)
        await expect(start_btn).to_be_enabled()
        await start_btn.click()

    async def click_spawn_page(browser, username):
        """spawn the server for one user via the Spawn page button, index = 0 or 1"""
        spawn_btn_xpath = f'//a[contains(@href, "spawn/{username}")]/button[contains(@class, "btn-light")]'
        spawn_btn = browser.locator(spawn_btn_xpath)
        await expect(spawn_btn).to_be_enabled()
        async with browser.expect_navigation(url=f"**/user/{username}/"):
            await spawn_btn.click()

    async def click_access_server(browser, username):
        """access to the server for users via the Access Server button"""
        access_btn_xpath = f'//a[contains(@href, "user/{username}")]/button[contains(@class, "btn-primary")]'
        access_btn = browser.locator(access_btn_xpath)
        await expect(access_btn).to_be_enabled()
        await access_btn.click()
        await browser.go_back()

    async def click_stop_button(browser, username):
        """stop the server for one user via the Stop Server button"""
        stop_btn_xpath = f'//a[contains(@href, "user/{username}")]/preceding-sibling::button[contains(@class, "stop-button")]'
        stop_btn = browser.locator(stop_btn_xpath)
        await expect(stop_btn).to_be_enabled()
        await stop_btn.click()

    user1, user2 = create_list_of_users(create_user_with_scopes, 2)
    await open_admin_page(app, browser, admin_user)
    await browser.wait_for_load_state("networkidle")
    users = await browser.locator('//td[@data-testid="user-row-name"]').all()
    users_list = [await user.text_content() for user in users]
    users_list = [user.strip() for user in users_list]
    assert {user1.name, user2.name}.issubset({e for e in users_list})

    # check that all users have correct link for Spawn Page
    spawn_page_btns = browser.locator(
        '//*[@data-testid="user-row-server-activity"]//a[contains(@href, "spawn/")]'
    )
    spawn_page_btns_list = await spawn_page_btns.all()
    for user, spawn_page_btn in zip(users, spawn_page_btns_list):
        user_from_table = await user.text_content()
        user_from_table = user_from_table.strip()
        link = await spawn_page_btn.get_attribute('href')
        assert f"/spawn/{user_from_table}" in link

    # click on Start button
    await click_start_server(browser, user1.name)
    await expect(browser.get_by_role("button", name="Stop Server")).to_have_count(1)
    await expect(browser.get_by_role("button", name="Start Server")).to_have_count(
        len(users_list) - 1
    )
    await expect(browser.get_by_role("button", name="Spawn Page")).to_have_count(
        len(users_list) - 1
    )

    # click on Spawn page button
    await click_spawn_page(browser, user2.name)
    await expect(browser).to_have_url(re.compile(".*" + f"/user/{user2.name}/"))

    # open/return to the Admin page
    admin_page = url_path_join(public_host(app), app.hub.base_url, "admin")
    await browser.goto(admin_page)
    await expect(browser.get_by_role("button", name="Stop Server")).to_have_count(2)
    await expect(browser.get_by_role("button", name="Access Server")).to_have_count(2)
    await expect(browser.get_by_role("button", name="Start Server")).to_have_count(
        len(users_list) - 2
    )

    # click on the Access button
    await click_access_server(browser, user1.name)
    await expect(browser.get_by_role("button", name="Stop Server")).to_have_count(2)
    await expect(browser.get_by_role("button", name="Start Server")).to_have_count(
        len(users_list) - 2
    )

    # click on Stop button for both users
    [
        await click_stop_button(browser, username)
        for username in (user1.name, user2.name)
    ]
    await expect(browser.get_by_role("button", name="Stop Server")).to_have_count(0)
    await expect(browser.get_by_role("button", name="Access Server")).to_have_count(0)
    await expect(browser.get_by_role("button", name="Start Server")).to_have_count(
        len(users_list)
    )
    await expect(browser.get_by_role("button", name="Spawn Page")).to_have_count(
        len(users_list)
    )


@pytest.mark.parametrize(
    "case",
    [
        "fresh",
        "invalid",
        "valid-prefix-invalid-root",
        "valid-prefix-invalid-other-prefix",
    ],
)
async def test_login_xsrf_initial_cookies(app, browser, case, username):
    """Test that login works with various initial states for xsrf tokens

    Page will be reloaded with correct values
    """
    hub_root = public_host(app)
    hub_url = url_path_join(public_host(app), app.hub.base_url)
    hub_parent = hub_url.rstrip("/").rsplit("/", 1)[0] + "/"
    login_url = url_path_join(
        hub_url, url_concat("login", {"next": url_path_join(app.base_url, "/hub/home")})
    )
    # start with all cookies cleared
    await browser.context.clear_cookies()
    if case == "invalid":
        await browser.context.add_cookies(
            [{"name": "_xsrf", "value": "invalid-hub-prefix", "url": hub_url}]
        )
    elif case.startswith("valid-prefix"):
        if "invalid-root" in case:
            invalid_url = hub_root
        else:
            invalid_url = hub_parent
        await browser.goto(login_url)
        # first visit sets valid xsrf cookie
        cookies = await browser.context.cookies()
        assert len(cookies) == 1
        # second visit is also made with invalid xsrf on `/`
        # handling of this behavior is undefined in HTTP itself!
        # _either_ the invalid cookie on / is ignored
        # _or_ both will be cleared
        # currently, this test assumes the observed behavior,
        # which is that the invalid cookie on `/` has _higher_ priority
        await browser.context.add_cookies(
            [{"name": "_xsrf", "value": "invalid-root", "url": invalid_url}]
        )
        cookies = await browser.context.cookies()
        assert len(cookies) == 2

    # after visiting page, cookies get re-established
    await browser.goto(login_url)
    cookies = await browser.context.cookies()
    print(cookies)
    cookie = cookies[0]
    assert cookie['name'] == '_xsrf'
    assert cookie["path"] == app.hub.base_url

    # next page visit, cookies don't change
    await browser.goto(login_url)
    cookies_2 = await browser.context.cookies()
    assert cookies == cookies_2
    # login is successful
    await login(browser, username, username)


async def test_prefix_redirect_not_running(browser, app, user):
    # tests PrefixRedirectHandler for stopped servers
    await login_home(browser, app, user.name)
    # visit user url (includes subdomain, if enabled)
    url = public_url(app, user, "/tree/")
    await browser.goto(url)
    # make sure we end up on the Hub (domain included)
    expected_url = url_path_join(public_url(app), f"hub/user/{user.name}/tree/")
    await expect(browser).to_have_url(expected_url)


def _cookie_dict(cookie_list):
    """Convert list of cookies to dict of the form

    { 'path': {'key': {cookie} } }
    """
    cookie_dict = {}
    for cookie in cookie_list:
        path_cookies = cookie_dict.setdefault(cookie['path'], {})
        path_cookies[cookie['name']] = cookie
    return cookie_dict


async def test_singleuser_xsrf(
    app,
    browser,
    user,
    create_user_with_scopes,
    full_spawn,
    named_servers,  # noqa: F811
):
    # full login process, checking XSRF handling
    # start two servers
    target_user = user
    target_start = asyncio.ensure_future(target_user.spawn())

    browser_user = create_user_with_scopes("self", "access:servers")
    # login browser_user
    login_url = url_path_join(public_host(app), app.hub.base_url, "login")
    await browser.goto(login_url)
    await login(browser, browser_user.name, browser_user.name)
    # end up at single-user
    await expect(browser).to_have_url(re.compile(rf".*/user/{browser_user.name}/.*"))
    # wait for target user to start, too
    await target_start
    await app.proxy.add_user(target_user)

    # visit target user, sets credentials for second server
    await browser.goto(public_url(app, target_user))
    await expect(browser).to_have_url(re.compile(r".*/oauth2/authorize"))
    auth_button = browser.locator('//button[@type="submit"]')
    await expect(auth_button).to_be_enabled()
    await auth_button.click()
    await expect(browser).to_have_url(re.compile(rf".*/user/{target_user.name}/.*"))

    # at this point, we are on a page served by target_user,
    # logged in as browser_user
    # basic check that xsrf isolation works
    cookies = await browser.context.cookies()
    cookie_dict = _cookie_dict(cookies)
    pprint.pprint(cookie_dict)

    # we should have xsrf tokens for both singleuser servers and the hub
    target_prefix = target_user.prefix
    user_prefix = browser_user.prefix
    hub_prefix = app.hub.base_url
    assert target_prefix in cookie_dict
    assert user_prefix in cookie_dict
    assert hub_prefix in cookie_dict
    target_xsrf = cookie_dict[target_prefix].get("_xsrf", {}).get("value")
    assert target_xsrf
    user_xsrf = cookie_dict[user_prefix].get("_xsrf", {}).get("value")
    assert user_xsrf
    hub_xsrf = cookie_dict[hub_prefix].get("_xsrf", {}).get("value")
    assert hub_xsrf
    assert hub_xsrf != target_xsrf
    assert hub_xsrf != user_xsrf
    assert target_xsrf != user_xsrf

    # we are on a page served by target_user
    # check that we can't access

    async def fetch_user_page(path, params=None):
        url = url_path_join(public_url(app, browser_user), path)
        if params:
            url = url_concat(url, params)
        status = await browser.evaluate(
            """
            async (user_url) => {
              try {
                response = await fetch(user_url);
              } catch (e) {
                return 'error';
              }
              return response.status;
            }
            """,
            url,
        )
        return status

    if app.subdomain_host:
        expected_status = 'error'
    else:
        expected_status = 403
    status = await fetch_user_page("/api/contents")
    assert status == expected_status
    status = await fetch_user_page("/api/contents", params={"_xsrf": target_xsrf})
    assert status == expected_status

    if not app.subdomain_host:
        expected_status = 200
    status = await fetch_user_page("/api/contents", params={"_xsrf": user_xsrf})
    assert status == expected_status

    # check that we can't iframe the other user's page
    async def iframe(src):
        return await browser.evaluate(
            """
            async (src) => {
                const frame = document.createElement("iframe");
                frame.src = src;
                return new Promise((resolve, reject) => {
                    frame.addEventListener("load", (event) => {
                        if (frame.contentDocument) {
                            resolve("got document!");
                        } else {
                            resolve("blocked")
                        }
                    });
                    setTimeout(() => {
                        // some browsers (firefox) never fire load event
                        // despite spec appasrently stating it must always do so,
                        // even for rejected frames
                        resolve("timeout")
                    }, 3000)

                    document.body.appendChild(frame);
                });
            }
            """,
            src,
        )

    hub_iframe = await iframe(url_path_join(public_url(app), "hub/admin"))
    assert hub_iframe in {"timeout", "blocked"}
    user_iframe = await iframe(public_url(app, browser_user))
    assert user_iframe in {"timeout", "blocked"}

    # check that server page can still connect to its own kernels
    token = target_user.new_api_token(scopes=["access:servers!user"])

    async def test_kernel(kernels_url):
        headers = {"Authorization": f"Bearer {token}"}
        r = await async_requests.post(kernels_url, headers=headers)
        r.raise_for_status()
        kernel = r.json()
        kernel_id = kernel["id"]
        kernel_url = url_path_join(kernels_url, kernel_id)
        kernel_ws_url = "ws" + url_path_join(kernel_url, "channels")[4:]
        try:
            result = await browser.evaluate(
                """
                async (ws_url) => {
                    ws = new WebSocket(ws_url);
                    finished = await new Promise((resolve, reject) => {
                        ws.onerror = (err) => {
                            reject(err);
                        };
                        ws.onopen = () => {
                            resolve("ok");
                        };
                    });
                    return finished;
                }
                """,
                kernel_ws_url,
            )
        finally:
            r = await async_requests.delete(kernel_url, headers=headers)
            r.raise_for_status()
        assert result == "ok"

    kernels_url = url_path_join(public_url(app, target_user), "/api/kernels")
    await test_kernel(kernels_url)

    # final check: make sure named servers work.
    # first, visit spawn page to launch server,
    # will issue cookies, etc.
    server_name = "named"
    url = url_path_join(
        public_host(app),
        url_path_join(app.base_url, f"hub/spawn/{browser_user.name}/{server_name}"),
    )
    await browser.goto(url)
    await expect(browser).to_have_url(
        re.compile(rf".*/user/{browser_user.name}/{server_name}/.*")
    )
    # from named server URL, make sure we can talk to a kernel
    token = browser_user.new_api_token(scopes=["access:servers!user"])
    # named-server URL
    kernels_url = url_path_join(
        public_url(app, browser_user), server_name, "api/kernels"
    )
    await test_kernel(kernels_url)
    # go back to user's own page, test again
    # make sure we didn't break anything
    await browser.goto(public_url(app, browser_user))
    await test_kernel(url_path_join(public_url(app, browser_user), "api/kernels"))
