import os
from functools import wraps
from html import escape
from urllib.parse import urlparse

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler, authenticated

from jupyterhub.services.auth import HubOAuthCallbackHandler, HubOAuthenticated
from jupyterhub.utils import url_path_join

SCOPE_PREFIX = "custom:grades"
READ_SCOPE = f"{SCOPE_PREFIX}:read"
WRITE_SCOPE = f"{SCOPE_PREFIX}:write"


def require_scope(scopes):
    """Decorator to require scopes

    For use if multiple methods on one Handler
    may want different scopes,
    so class-level .hub_scopes is insufficient
    (e.g. read for GET, write for POST).
    """
    if isinstance(scopes, str):
        scopes = [scopes]

    def wrap(method):
        """The actual decorator"""

        @wraps(method)
        @authenticated
        def wrapped(self, *args, **kwargs):
            self.hub_scopes = scopes
            return method(self, *args, **kwargs)

        return wrapped

    return wrap


class MyGradesHandler(HubOAuthenticated, RequestHandler):
    # no hub_scopes, anyone with access to this service
    # will be able to visit this URL

    @authenticated
    def get(self):
        self.write("<h1>My grade</h1>")
        name = self.current_user["name"]
        grades = self.settings["grades"]
        self.write(f"<p>My name is: {escape(name)}</p>")
        if name in grades:
            self.write(f"<p>My grade is: {escape(str(grades[name]))}</p>")
        else:
            self.write("<p>No grade entered</p>")
        if READ_SCOPE in self.current_user["scopes"]:
            self.write('<a href="grades/">enter grades</a>')


class GradesHandler(HubOAuthenticated, RequestHandler):
    # default scope for this Handler: read-only
    hub_scopes = [READ_SCOPE]

    def _render(self):
        grades = self.settings["grades"]
        self.write("<h1>All grades</h1>")
        self.write("<table>")
        self.write("<tr><th>Student</th><th>Grade</th></tr>")
        for student, grade in grades.items():
            qstudent = escape(student)
            qgrade = escape(str(grade))
            self.write(
                f"""
                <tr>
                 <td class="student">{qstudent}</td>
                 <td class="grade">{qgrade}</td>
                </tr>
                """
            )
        if WRITE_SCOPE in self.current_user["scopes"]:
            self.write("Enter grade:")
            self.write(
                """
                <form action=. method=POST>
                    <input name=student placeholder=student></input>
                    <input kind=number name=grade placeholder=grade></input>
                    <input type="submit" value="Submit">
                """
            )

    @require_scope([READ_SCOPE])
    async def get(self):
        self._render()

    # POST requires WRITE_SCOPE instead of READ_SCOPE
    @require_scope([WRITE_SCOPE])
    async def post(self):
        name = self.get_argument("student")
        grade = self.get_argument("grade")
        self.settings["grades"][name] = grade
        self._render()


def main():
    base_url = os.environ['JUPYTERHUB_SERVICE_PREFIX']

    app = Application(
        [
            (base_url, MyGradesHandler),
            (url_path_join(base_url, 'grades/'), GradesHandler),
            (
                url_path_join(base_url, 'oauth_callback'),
                HubOAuthCallbackHandler,
            ),
        ],
        cookie_secret=os.urandom(32),
        grades={"student": 53},
    )

    http_server = HTTPServer(app)
    url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])

    http_server.listen(url.port, url.hostname)
    try:
        IOLoop.current().start()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
