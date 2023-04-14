import pytest
from playwright.async_api import async_playwright


@pytest.fixture()
async def browser():
    # browser_type in ["chromium", "firefox", "webkit"]
    async with async_playwright() as playwright:
        browser = await playwright.firefox.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        yield page
        await context.clear_cookies()
        await browser.close()
