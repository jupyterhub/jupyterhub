import pytest
from selenium import webdriver


@pytest.fixture(scope="session")
def browser_session():
    """Re-use one browser instance for the test session"""
    options = webdriver.FirefoxOptions()
    options.add_argument("-headless")
    driver = webdriver.Firefox(options=options)
    yield driver
    driver.close()
    driver.quit()


@pytest.fixture
def browser(browser_session, cleanup_after):
    """Get the browser session for one test

    cookies are cleared after each test
    """
    yield browser_session
    browser_session.delete_all_cookies()
