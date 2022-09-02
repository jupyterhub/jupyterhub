from selenium.webdriver.common.by import By


class LoginPageLocators:

    FORM_LOGIN = (By.XPATH, '//*[@id="login-main"]/form')
    """/hub/login?next=%2Fhub%2F" , "/hub/login?next="""

    SIGN_IN = (By.CLASS_NAME, 'auth-form-header')
    ACCOUNT = (By.ID, "username_input")
    PASSWORD = (By.ID, "password_input")
    LOGIN_BUTTON = (By.ID, "login_submit")
    """<img src="/hub/logo" alt="JupyterHub" class="jpy-logo" title="Home">
    """
    LOGO = (By.ID, "jupyterhub-logo")
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

    """<a href="/hub/home">Home</a>"""
    LINK_HOME = (By.CSS_SELECTOR, "a[href*='/hub/home']")

    """<a href="/hub/token">Token</a>"""
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

    BUTTON_START_SERVER = (By.ID, "start")
    BUTTON_STOP_SERVER = (By.ID, "stop")

    """<button class="revoke-token-btn btn btn-xs btn-danger">revoke</button>"""
    BUTTON_REVOKE = ()


class TokenPageLocators:
    """<button type="submit" class="btn btn-lg btn-jupyter">
      Request new API token
    </button>"""

    BUTTON_API_REQ = (By.XPATH, '//*[@id="request-token-form"]/div[1]/button')

    """<input id="token-note" class="form-control" placeholder="note to identify your new token">"""
    INPUT_TOKEN = (By.ID, "token-note")

    """ <select id="token-expiration-seconds" class="form-control">
      <option value="3600">1 Day</option>
          <option value="86400">1 Week</option>
          <option value="604800">1 Month</option>
          <option value="" selected="selected">Never</option>
        </select>    """

    LIST_EXP_TOKEN_FIELD = (By.ID, "token-expiration-seconds")
    LIST_EXP_TOKEN_OPT = (By.XPATH, '//option')

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
