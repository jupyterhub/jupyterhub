import pytest
from selenium import webdriver


@pytest.fixture()
def browser():
    options = webdriver.FirefoxOptions()
    options.set_headless()
    driver = webdriver.Firefox(firefox_options=options)
    yield driver
    driver.close()
    driver.quit()
