"""Using for testing via the Selenium WebDriver for elements localization"""

from selenium.webdriver.common.by import By


class BarLocators:
    """class for handling the Menu bar page locators"""

    LINK_HOME_BAR = (By.CSS_SELECTOR, "div.container-fluid a")
    USER_NAME = (By.CLASS_NAME, 'navbar-text')


class LoginPageLocators:
    """class for handling the login page locators"""

    FORM_LOGIN = (By.XPATH, '//*[@id="login-main"]/form')
    ACCOUNT = (By.ID, "username_input")
    PASSWORD = (By.ID, "password_input")
    ERROR_INVALID_CREDANTIALS = (By.CSS_SELECTOR, "p.login_error")


class SpawningPageLocators:
    """class for handling the Spawning page locators"""

    BUTTONS_SERVER = (By.CSS_SELECTOR, "div.text-center a")
    TEXT_SERVER_TITLE = (By.CSS_SELECTOR, "div.text-center h1")

    TEXT_SERVER = (By.CSS_SELECTOR, "div.text-center p")
    TEXT_SERVER_NOT_RUN_YET = "Server not running"
    TEXT_SERVER_NOT_RUNNING = "Your server is not running. Would you like to start it?"

    TEXT_SERVER_STARTING = "Your server is starting up."
    TEXT_SERVER_REDIRECT = (
        "You will be redirected automatically when it's ready for you."
    )
    PROGRESS_MESSAGE = (By.ID, "progress-message")
    PROGRESS_PRO = (By.ID, "sr-progress")
    PROGRESS_STATUS = (By.CLASS_NAME, "sr-only")
    TEXT = (By.ID, "starting")


class HomePageLocators:
    """class for handling the home page locators"""

    BUTTONS_SERVER = (By.CSS_SELECTOR, "div.text-center a")
    TEXT_SERVER = (By.CSS_SELECTOR, "div.text-center p")
    TEXT_SERVER_STARTING = "Your server is starting up."
    TEXT_SERVER_REDIRECT = (
        "You will be redirected automatically when it's ready for you."
    )


class TokenPageLocators:
    """class for handling the Token page locators"""

    BUTTON_API_REQ = (
        By.XPATH,
        '//form[@id="request-token-form"]//button[@type="submit"]',
    )
    LIST_EXP_TOKEN_FIELD = (By.ID, "token-expiration-seconds")
    LIST_EXP_TOKEN_OPT = (By.XPATH, '//option')
    """ 1 Hour,1 Day,1 Week, Never """

    LIST_EXP_TOKEN_OPT_DICT = {
        '1 Hour': '3600',
        '1 Day': '86400',
        '1 Week': '604800',
        'Never': '',
    }
    """'1 Hour': '3600','1 Day': '86400','1 Week': '604800','Never': ''
    displayed options: the values in sec"""

    NEVER_EXP = (By.XPATH, '//*[@id="token-expiration-seconds"]/option[4]')
    TEXT = "Copy this token. You won't be able to see it again, but you can always come back here to get a new one."

    # API Tokens table
    TOKEN_TABLE = (By.XPATH, '//h2[text()="API Tokens"]//following::table')
    TOKEN_TABLE_HEADER = (By.XPATH, '//h2[text()="API Tokens"]//following::table/thead')
    TOKEN_TABLE_HEAD_LIST = ['Note', 'Last used', 'Created', 'Expires at']
    TOKEN_TABLE_BODY = (By.TAG_NAME, 'tbody')
    TOKEN_TABLE_ROWS_BY_CLASS = (
        By.XPATH,
        '//h2[text()="API Tokens"]//following::table//tr[@class="token-row"]',
    )
    BUTTON_REVOKE_TOKEN = (By.XPATH, '//tr/td[5]/button')

    # Authorized Applications
    AUTH_TABLE = (By.XPATH, '//h2[text()="Authorized Applications"]//following::table')
    AUTH_TABLE_HEAD_LIST = ['Application', 'Last used', 'First authorized']
    AUTH_TABLE_HEADER = (
        By.XPATH,
        '//h2[text()="Authorized Applications"]//following::table/thead',
    )
    AUTH_TABLE_HEAD = (By.TAG_NAME, 'thead')
    AUTH_TABLE_BODY = (By.TAG_NAME, 'tbody')
    AUTH_TABLE_ROWS_BY_CLASS = (
        By.XPATH,
        '//h2[text()="Authorized Applications"]//following::table//tr[@class="token-row"]',
    )
    BUTTON_REVOKE_AUTH = (By.XPATH, '//tr/td[4]/button')
