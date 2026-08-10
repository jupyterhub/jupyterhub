import re

import pytest
from playwright.async_api import expect
from tornado.httputil import url_concat

from jupyterhub.utils import url_path_join

from ..conftest import new_username
from ..utils import add_user, api_request, public_host
from .test_browser import login

pytestmark = pytest.mark.browser


async def test_share_code_flow_full(app, browser, full_spawn, create_user_with_scopes):
    share_user = add_user(app.db, name=new_username("share_with"))
    user = create_user_with_scopes(
        "shares!user", "self", f"read:users:name!user={share_user.name}"
    )
    # start server
    await user.spawn("")
    await app.proxy.add_user(user)
    spawner = user.spawner

    # issue_code
    share_url = f"share-codes/{user.name}/{spawner.name}"
    r = await api_request(
        app,
        share_url,
        method="post",
        name=user.name,
    )
    r.raise_for_status()
    share_model = r.json()
    assert "code" in share_model
    code = share_model["code"]

    # visit share page
    accept_share_url = url_path_join(public_host(app), app.hub.base_url, "accept-share")
    accept_share_url = url_concat(accept_share_url, {"code": code})
    await browser.goto(accept_share_url)
    # wait for login
    await expect(browser).to_have_url(re.compile(r".*/login"))
    # login
    await login(browser, share_user.name)
    # back to accept-share page
    await expect(browser).to_have_url(re.compile(r".*/accept-share"))

    header_text = await browser.locator("p.lead").first.text_content()
    assert f"access {user.name}'s server" in header_text
    assert f"You ({share_user.name})" in header_text
    # TODO verify form
    submit = browser.locator('//button[@type="submit"]')
    await submit.click()

    # redirects to server, which triggers oauth approval
    await expect(browser).to_have_url(re.compile(r".*/oauth2/authorize"))
    submit = browser.locator('//button[@type="submit"]')
    await submit.click()

    # finally, we are at the server!
    await expect(browser).to_have_url(re.compile(f".*/user/{user.name}/.*"))


@pytest.mark.parametrize(
    "next_url, expected_next",
    [
        ("/hub/home", None),
        # note: these may be nonsensical, but at least they route correctly (and will 404)
        ("/hub/home'><img>", None),
        ('/hub/home"><img>', None),
        ('/hub/home?a=5&b=10', None),
        ('/hub/">injected</a><a>', None),
        ('https://example.com/', "DEFAULT"),
        ('///example.com/', "DEFAULT"),
    ],
)
async def test_share_code_next(app, browser, user, next_url, expected_next):
    if expected_next is None:
        expected_next = next_url
    elif expected_next == "DEFAULT":
        expected_next = user.base_url
    share_user = add_user(app.db, name=new_username("share_with"))
    # issue_code
    share_url = f"share-codes/{user.name}/"
    r = await api_request(
        app,
        share_url,
        method="post",
    )
    r.raise_for_status()
    share_model = r.json()
    assert "code" in share_model
    code = share_model["code"]

    # visit share page
    accept_share_url = url_path_join(public_host(app), app.hub.base_url, "accept-share")
    accept_share_url = url_concat(accept_share_url, {"code": code, "next": next_url})
    await browser.goto(accept_share_url)
    # wait for login
    await expect(browser).to_have_url(re.compile(r".*/login"))
    # login
    await login(browser, share_user.name)
    # back to accept-share page
    await expect(browser).to_have_url(re.compile(r".*/accept-share"))
    link = browser.locator(".card-footer").locator("a")
    await expect(link).to_have_count(1)
    href = await link.get_attribute("href")
    text = await link.inner_text()
    # text and href have html unescaping applied
    # if both are intact, that means nothing was mis-parsed
    assert text == expected_next
    assert href == expected_next
