import pytest
from selenium import webdriver


@pytest.fixture()
def browser():
    driver = webdriver.Firefox()
    yield driver
    driver.close()
    driver.quit()
