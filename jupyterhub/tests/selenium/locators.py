"""Using for testing via the Selenium WebDriver for elements localization"""

from selenium.webdriver.common.by import By


class BarLocators:
    """class for handling the Menu bar page locators"""

    LINK_HOME_BAR = (By.CSS_SELECTOR, "div.container-fluid a")
    LOGO = (By.TAG_NAME, "img")
    LOGO_LINK = (By.XPATH, '//*[@id="jupyterhub-logo"]/a')
    LOGO_TITLE = (By.XPATH, '//*[@id="jupyterhub-logo"]/a/img')
    LINK_HOME = (By.CSS_SELECTOR, "a[href*='/hub/home']")
    LINK_TOKEN = (By.CSS_SELECTOR, "a[href*='/hub/token']")
    USER_NAME = (By.CLASS_NAME, 'navbar-text')
    BUTTON_LOGOUT = (By.ID, "logout")


class LoginPageLocators:
    """class for handling the login page locators"""

    FORM_LOGIN = (By.XPATH, '//*[@id="login-main"]/form')
    SIGN_IN = (By.CLASS_NAME, 'auth-form-header')
    ACCOUNT = (By.ID, "username_input")
    PASSWORD = (By.ID, "password_input")
    LOGIN_BUTTON = (By.ID, "login_submit")
    ERROR_INVALID_CREDANTIALS = (By.CSS_SELECTOR, "p.login_error")
    PAGE_TITLE = 'JupyterHub'
    ERROR_MESSAGES_LOGIN = "Invalid username or password"
    ERROR_403 = (By.CLASS_NAME, "error")
    ERROR_MESSAGES_403 = (
        "Action is not authorized with current scopes; requires any of [admin-ui]"
    )


class SpawningPageLocators:

    BUTTONS_SERVER = (By.CSS_SELECTOR, "div.text-center a")
    BUTTON_START_SERVER = (By.ID, "start")
    BUTTON_LAUNCH_SERVER_NAME = "Launch Server"
    TEXT_SERVER_TITLE = (By.CSS_SELECTOR, "div.text-center h1")

    TEXT_SERVER = (By.CSS_SELECTOR, "div.text-center p")
    TEXT_SERVER_NOT_RUN_YET = "Server not running"
    TEXT_SERVER_NOT_RUNNING = "Your server is not running. Would you like to start it?"

    TEXT_SERVER_STARTING = "Your server is starting up."
    TEXT_SERVER_REDIRECT = (
        "You will be redirected automatically when it's ready for you."
    )
    PROGRESS = (By.CLASS_NAME, "progress")
    PROGRESS_BAR = (By.CLASS_NAME, "progress-bar")
    PROGRESS_MESSAGE = (By.ID, "progress-message")
    PROGRESS_PRO = (By.ID, "sr-progress")
    PROGRESS_STATUS = (By.CLASS_NAME, "sr-only")
    TEXT_PROGRESS_MESSAGE_SPWN = "Spawning server..."
    TEXT_PROGRESS_MESSAGE_READY = "Server ready at "
    TEXT = (By.ID, "starting")
    SERVER_READY = "Server ready"
    PROGRESS_DETAILS = (By.ID, "progress-details")
    TEXT_PROGRESS_DETAILS = "Event log"
    PROGRESS_LOG = (By.CLASS_NAME, "progress-log-event")


class HomePageLocators:
    """class for handling the home page locators"""

    BUTTONS_SERVER = (By.CSS_SELECTOR, "div.text-center a")
    BUTTON_START_SERVER = (By.ID, "start")
    BUTTON_START_SERVER_NAME = "My Server"
    BUTTON_START_SERVER_NAME_DOWN = "Start My Server"
    BUTTON_STOP_SERVER = (By.ID, "stop")
    BUTTON_STOP_SERVER_NAME = "Stop My Server"
    TEXT_SERVER = (By.CSS_SELECTOR, "div.text-center p")
    TEXT_SERVER_STARTING = "Your server is starting up."
    TEXT_SERVER_REDIRECT = (
        "You will be redirected automatically when it's ready for you."
    )


class TokenPageLocators:
    """class for handling the Token page locators"""

    # Request the token
    BUTTON_API_REQ_NAME = 'Request new API token'
    BUTTON_API_REQ = (
        By.XPATH,
        '//form[@id="request-token-form"]//button[@type="submit"]',
    )
    INPUT_TOKEN = (By.ID, "token-note")
    """<input id="token-note" class="form-control" placeholder="note to identify your new token">"""

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
    HOUR1 = (By.CSS_SELECTOR, "option[value='3600']")
    DAY1 = (By.CSS_SELECTOR, "option[value='86400']")
    WEEK1 = (By.CSS_SELECTOR, "option[value='604800']")

    PANEL_AREA = (By.ID, 'token-area')
    PANEL_TOKEN = (By.CLASS_NAME, 'panel-heading')
    PANEL_TOKEN_TITLE = "Your new API Token"

    RESULT_TOKEN = (By.ID, 'token-result')
    TEXT = "Copy this token. You won't be able to see it again, but you can always come back here to get a new one."

    # API Tokens table
    TABLE_API = (By.XPATH, '/html/body/div[1]/div[3]/table')
    TABLE_API_HEAD = (By.TAG_NAME, 'thead')
    TABLE_API_HEAD_LIST = ['Note', 'Last used', 'Created', 'Expires at']
    TABLE_API_BODY = (By.TAG_NAME, 'tbody')
    TABLE_API_ROWS = (By.TAG_NAME, 'tr')
    TABLE_API_ROWS_BY_CLASS = (By.CLASS_NAME, 'token-row')
    TABLE_API_COLUMNS = (By.TAG_NAME, 'td')
    BUTTON_REVOKE = (By.XPATH, '//tr/td[5]/button')

    # Authorized Applications

    TABLE_AUTH = (By.XPATH, '/html/body/div[1]/div[4]/table')
    TABLE_AUTH_HEAD_LIST = ['Application', 'Last used', 'First authorized']
    TABLE_AUTH_HEAD = (By.TAG_NAME, 'thead')
    TABLE_AUTH_BODY = (By.TAG_NAME, 'tbody')
    TABLE_AUTH_ROWS = (By.TAG_NAME, 'tr')
    TABLE_AUTH_ROWS_BY_CLASS = (By.CLASS_NAME, 'token-row')
    TABLE_AUTH_COLUMNS = (By.TAG_NAME, 'td')
