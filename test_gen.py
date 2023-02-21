from playwright.sync_api import Page


def test_example(page: Page) -> None:
    page.goto("http://localhost:8000/hub/login?next=%2Fhub%2F")
    page.get_by_role("heading", name="Sign in").click()
    page.get_by_text(
        "Warning: JupyterHub seems to be served over an unsecured HTTP connection. We str"
    ).click()
    page.get_by_label("Username:").click()
    page.get_by_label("Username:").fill("hello")
    page.get_by_label("Password:").click()
    page.get_by_label("Password:").fill("hello")
    page.get_by_role("button", name="Sign in").click()
