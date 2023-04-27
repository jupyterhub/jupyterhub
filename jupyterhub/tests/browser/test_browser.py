"""Tests for the Playwright Python"""

import re

import pytest
from playwright.async_api import expect
from tornado.escape import url_escape
from tornado.httputil import url_concat

from jupyterhub.tests.utils import public_host, public_url, ujoin
from jupyterhub.utils import url_escape_path, url_path_join

pytestmark = pytest.mark.browser


async def login(browser, username, password):
    """filling the login form by user and pass_w parameters and iniate the login"""

    await browser.get_by_label("Username:").click()
    await browser.get_by_label("Username:").fill(username)
    await browser.get_by_label("Password:").click()
    await browser.get_by_label("Password:").fill(password)
    await browser.get_by_role("button", name="Sign in").click()


async def test_open_login_page(app, browser):
    login_url = url_path_join(public_host(app), app.hub.base_url, "login")
    await browser.goto(login_url)
    await expect(browser).to_have_url(re.compile(r".*/login"))
    await expect(browser).to_have_title("JupyterHub")
    form = browser.locator('//*[@id="login-main"]/form')
    await expect(form).to_be_visible()
    await expect(form.locator('//h1')).to_have_text("Sign in")


async def test_submit_login_form(app, browser, user):
    login_url = url_path_join(public_host(app), app.hub.base_url, "login")
    await browser.goto(login_url)
    await login(browser, user.name, password=user.name)
    expected_url = ujoin(public_url(app), f"/user/{user.name}/")
    await expect(browser).to_have_url(expected_url)


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
    login_url = url_path_join(public_host(app), app.hub.base_url, url)
    await browser.goto(login_url)
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
        await expect(browser).to_have_url(re.compile(".*/user/" + f"{user.name}/"))


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
    login_url = url_path_join(public_host(app), app.hub.base_url, "login")
    await browser.goto(login_url)
    await login(browser, username, pass_w)
    locator = browser.locator("p.login_error")
    expected_error_message = "Invalid username or password"
    # verify error message displayed and user stays on login page
    await expect(locator).to_be_visible()
    await expect(locator).to_contain_text(expected_error_message)
    await expect(browser).to_have_url(re.compile(".*/hub/login"))


# SPAWNING


async def open_spawn_pending(app, browser, user):
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
        public_host(app), app.hub.base_url, '/spawn-pending/' + user.name
    )
    await browser.goto(url_spawn)
    await expect(browser).to_have_url(url_spawn)


async def test_spawn_pending_server_not_started(
    app, browser, no_patience, user, slow_spawn
):
    # first request, no spawn is pending
    # spawn-pending shows button linking to spawn
    await open_spawn_pending(app, browser, user)
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
    f_string = re.escape(f"/hub/spawn/{user.name}")
    await expect(launch_btn).to_have_attribute('href', re.compile('.*' + f_string))


async def test_spawn_pending_progress(app, browser, no_patience, user, slow_spawn):
    """verify that the server process messages are showing up to the user
    when the server is going to start up"""

    # visit the spawn-pending page
    await open_spawn_pending(app, browser, user)
    launch_btn = browser.locator("//div[@class='text-center']").get_by_role(
        "button", name="Launch Server"
    )
    await expect(launch_btn).to_be_enabled()

    # begin starting the server
    async with browser.expect_navigation(
        url=re.compile(".*/spawn-pending/" + f"{user.name}")
    ):
        await launch_btn.click()
    # wait for progress message to appear
    progress = browser.locator("#progress-message")
    progress_message = await progress.inner_text()
    async with browser.expect_navigation(url=re.compile(".*/user/" + f"{user.name}/")):
        # wait for log messages to appear
        expected_messages = [
            "Server requested",
            "Spawning server...",
            f"Server ready at {app.base_url}user/{user.name}/",
        ]
        while not user.spawner.ready:
            logs_list = [
                await log.inner_text()
                for log in await browser.locator("div.progress-log-event").all()
            ]
            if progress_message:
                assert progress_message in expected_messages
            # race condition: progress_message _should_
            # be the last log message, but it _may_ be the next one
            if logs_list:
                assert progress_message
            assert logs_list == expected_messages[: len(logs_list)]
    await expect(browser).to_have_url(re.compile(".*/user/" + f"{user.name}/"))
    assert user.spawner.ready


async def test_spawn_pending_server_ready(app, browser, user):
    """verify that after a successful launch server via the spawn-pending page
    the user should see two buttons on the home page"""

    await open_spawn_pending(app, browser, user)
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


async def test_start_button_server_not_started(app, browser, user):
    """verify that when server is not started one button is availeble,
    after starting 2 buttons are available"""
    await open_home_page(app, browser, user)
    # checking that only one button is presented
    start_stop_btns = browser.locator('//div[@class="text-center"]').get_by_role(
        "button"
    )
    expected_btn_name = "Start My Server"
    await expect(start_stop_btns).to_be_enabled()
    await expect(start_stop_btns).to_have_count(1)
    await expect(start_stop_btns).to_have_text(expected_btn_name)
    f_string = re.escape(f"/hub/spawn/{user.name}")
    await expect(start_stop_btns).to_have_attribute('href', re.compile('.*' + f_string))
    async with browser.expect_navigation(url=re.compile(".*/user/" + f"{user.name}/")):
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
    f_string = re.escape(f"/user/{user.name}")
    await expect(start_stop_btns.nth(1)).to_have_attribute(
        'href', re.compile('.*' + f_string)
    )
    await expect(start_stop_btns.nth(0)).to_have_id("stop")
    await expect(start_stop_btns.nth(1)).to_have_id("start")


async def test_stop_button(app, browser, user):
    """verify that the stop button after stoping a server is not shown
    the start button is displayed with new name"""

    await open_home_page(app, browser, user)
    # checking that only one button is presented
    start_stop_btns = browser.locator('//div[@class="text-center"]').get_by_role(
        "button"
    )
    async with browser.expect_navigation(url=re.compile(".*/user/" + f"{user.name}/")):
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


async def test_token_request_form_and_panel(app, browser, user):
    """verify elements of the request token form"""

    await open_token_page(app, browser, user)
    request_btn = browser.locator('//div[@class="text-center"]').get_by_role("button")
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

    # check the list of tokens duration
    dropdown = browser.locator('#token-expiration-seconds')
    options = await dropdown.locator('option').all()
    expected_values_in_list = {
        '1 Hour': '3600',
        '1 Day': '86400',
        '1 Week': '604800',
        'Never': '',
    }
    actual_values = {
        await option.text_content(): await option.get_attribute('value')
        for option in options
    }
    assert actual_values == expected_values_in_list
    # get the value of the 'selected' attribute of the currently selected option
    selected_value = dropdown.locator('option[selected]')
    await expect(selected_value).to_have_text("Never")

    # verify that "Your new API Token" panel shows up with the new API token
    await request_btn.click()
    await browser.wait_for_load_state("load")
    expected_panel_token_heading = "Your new API Token"
    token_area = browser.locator('#token-area')
    await expect(token_area).to_be_visible()
    token_area_heading = token_area.locator('//div[@class="panel-heading"]')
    await expect(token_area_heading).to_have_text(expected_panel_token_heading)
    token_result = browser.locator('#token-result')
    await expect(token_result).not_to_be_empty()
    await expect(token_area).to_be_visible()
    # verify that "Your new API Token" panel is hidden after refresh the page
    await browser.reload(wait_until="load")
    await expect(token_area).to_be_hidden()
    api_token_table_area = browser.locator('//div[@class="row"]').nth(2)
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
async def test_request_token_expiration(app, browser, token_opt, note, user):
    """verify request token with the different options"""

    if token_opt == "server_up":
        # open the home page
        await open_home_page(app, browser, user)
        # start server via clicking on the Start button
        async with browser.expect_navigation(url=f"**/user/{user.name}/"):
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
        reqeust_btn = browser.locator('//div[@class="text-center"]').get_by_role(
            "button"
        )
        await reqeust_btn.click()
        await browser.reload(wait_until="load")
    # API Tokens table: verify that elements are displayed
    api_token_table_area = browser.locator('//div[@class="row"]').nth(2)
    await expect(api_token_table_area.get_by_role("table")).to_be_visible()
    await expect(api_token_table_area.locator("tr.token-row")).to_have_count(1)

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
    note_on_page = (
        await api_token_table_area.locator("tr.token-row")
        .get_by_role("cell")
        .nth(0)
        .inner_text()
    )
    assert note_on_page == expected_note
    last_used_text = (
        await api_token_table_area.locator("tr.token-row")
        .get_by_role("cell")
        .nth(1)
        .inner_text()
    )
    expires_at_text = (
        await api_token_table_area.locator("tr.token-row")
        .get_by_role("cell")
        .nth(3)
        .inner_text()
    )
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
    revoke_btn = (
        api_token_table_area.locator("tr.token-row")
        .get_by_role("cell")
        .nth(4)
        .get_by_role("button")
    )
    await expect(revoke_btn).to_be_visible()
    await expect(revoke_btn).to_have_text("revoke")


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
        # Start server via clicking on the Start button
        async with browser.expect_navigation(url=f"**/user/{user.name}/"):
            await browser.locator("#start").click()
    # open the token page
    next_url = url_path_join(public_host(app), app.base_url, '/hub/token')
    await browser.goto(next_url)
    await expect(browser).to_have_url(re.compile(".*/hub/token"))
    if token_type == "both" or token_type == "request_by_user":
        request_btn = browser.locator('//div[@class="text-center"]').get_by_role(
            "button"
        )
        await request_btn.click()
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
