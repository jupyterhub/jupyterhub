from selenium.webdriver.common.by import By


class LoginPageLocators:
    """class for handling the login page locators"""

    FORM_LOGIN = (By.XPATH, '//*[@id="login-main"]/form')
    SIGN_IN = (By.CLASS_NAME, 'auth-form-header')
    ACCOUNT = (By.ID, "username_input")
    PASSWORD = (By.ID, "password_input")
    LOGIN_BUTTON = (By.ID, "login_submit")
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
    """class for handling the home page locators"""

    LINK_HOME_BAR = (By.CSS_SELECTOR, "div.container-fluid a")
    LINK_HOME = (By.CSS_SELECTOR, "a[href*='/hub/home']")
    LINK_TOKEN = (By.CSS_SELECTOR, "a[href*='/hub/token']")
    BUTTON_LOGOUT = (By.ID, "logout")
    BUTTON_START_SERVER = (By.ID, "start")
    BUTTON_STOP_SERVER = (By.ID, "stop")


class TokenPageLocators:
    """class for handling the Token page locators"""

    BUTTON_API_REQ = (By.XPATH, '//*[@id="request-token-form"]/div[1]/button')
    INPUT_TOKEN = (By.ID, "token-note")
    LIST_EXP_TOKEN_FIELD = (By.ID, "token-expiration-seconds")
    LIST_EXP_TOKEN_OPT = (By.XPATH, '//option')
    NEVER_EXP = (By.ID, "Never")
    DAY1 = (By.ID, "3600")
    PANEL_AREA = (By.ID, 'token-area')
    PANEL_TOKEN = (By.CLASS_NAME, 'panel-heading')
    RESULT_TOKEN = (By.ID, 'token-result')
    TEXT = "Copy this token. You won't be able to see it again, but you can always come back here to get a new one."
