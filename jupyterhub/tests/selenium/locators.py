from selenium.webdriver.common.by import By


class LoginPageLocators:

    FORM_LOGIN = (By.XPATH, '//*[@id="login-main"]/form')
    SIGN_IN = (By.CLASS_NAME, 'auth-form-header')
    ACCOUNT = (By.ID, "username_input")
    PASSWORD = (By.ID, "password_input")
    LOGIN_BUTTON = (By.ID, "login_submit")
    LOGO = (
        By.ID,
        "jupyterhub-logo",
    )  # <img src="/hub/logo" alt="JupyterHub" class="jpy-logo" title="Home">
    LOGO_LINK = (By.XPATH, '//*[@id="jupyterhub-logo"]/a')
    LOGO_TITLE = (By.XPATH, '//*[@id="jupyterhub-logo"]/a/img')
    ERROR_INVALID_CREDANTIALS = (By.CSS_SELECTOR, "p.login_error")
    PAGE_TITLE = 'JupyterHub'
    ERROR_MESSAGES_LOGIN = "Invalid username or password"

    ERROR_403 = (By.CLASS_NAME, "error")
    ERROR_MESSAGES_403 = (
        "Action is not authorized with current scopes; requires any of [admin-ui]"
    )


class HomePageLocators:
    """http://127.0.0.1:8000/hub/home"""

    LINK_HOME_BAR = (By.CSS_SELECTOR, "div.container-fluid a")

    LINK_HOME = (By.CSS_SELECTOR, "a[href*='/hub/home']")
    LINK_TOKEN = (By.CSS_SELECTOR, "a[href*='/hub/token']")

    """<p class="navbar-text">username</p>"""
    USER_NAME = (By.XPATH, "to be done")

    """<a id="logout" role="button" class="navbar-btn btn-sm btn btn-default" 
    href="/hub/logout"> <i aria-hidden="true" class="fa fa-sign-out"></i> Logout</a>
    """
    BUTTON_LOGOUT = (By.ID, "logout")

    """<a id="start" role="button" class="btn btn-lg btn-primary" href="/hub/spawn/username">
      Start
      My Server
      </a>"""
    """has 2 names My server and Start My server"""
    # "/hub/spawn/username">= in case the server is not running, in case the server is running = href="user/username"

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

    # Request the token
    BUTTON_API_REQ_NAME = 'Request new API token'

    BUTTON_API_REQ = (By.XPATH, '//*[@id="request-token-form"]/div[1]/button')

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
    """displayed option :the value in sec"""

    NEVER_EXP = (By.ID, "Never")
    DAY1 = (By.ID, "3600")

    """<div class="panel-heading">
            Your new API Token
          </div>"""

    """ style= "display: none;" when it is hidden"""
    PANEL_AREA = (By.ID, 'token-area')
    PANEL_TOKEN = (By.CLASS_NAME, 'panel-heading')

    """<span id="token-result">7226c895c101455889a82ca908251c68</span>"""
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

    BUTTON_REVOKE = (By.NAME, 'revoke')
    # BUTTON_REVOKE = (By.CLASS_NAME, 'revoke-token-btn btn btn-xs btn-danger')
    """<button class="revoke-token-btn btn btn-xs btn-danger">revoke</button>"""
