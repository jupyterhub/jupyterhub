import React from "react";
import "@testing-library/jest-dom";
import { act } from "react-dom/test-utils";
import userEvent from "@testing-library/user-event";
import {
  render,
  screen,
  fireEvent,
  getByText,
  getAllByRole,
} from "@testing-library/react";
import { HashRouter, Switch } from "react-router-dom";
import { CompatRouter, useSearchParams } from "react-router-dom-v5-compat";
import { Provider, useSelector } from "react-redux";
import { createStore } from "redux";
// eslint-disable-next-line
import regeneratorRuntime from "regenerator-runtime";

import ServerDashboard from "./ServerDashboard";
import { initialState, reducers } from "../../Store";
import * as sinon from "sinon";

let clock;

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useSelector: jest.fn(),
}));
jest.mock("react-router-dom-v5-compat", () => ({
  ...jest.requireActual("react-router-dom-v5-compat"),
  useSearchParams: jest.fn(),
}));

var serverDashboardJsx = (spy) => (
  <Provider store={createStore(mockReducers, mockAppState())}>
    <HashRouter>
      <CompatRouter>
        <Switch>
          <ServerDashboard
            updateUsers={spy}
            shutdownHub={spy}
            startServer={spy}
            stopServer={spy}
            startAll={spy}
            stopAll={spy}
          />
        </Switch>
      </CompatRouter>
    </HashRouter>
  </Provider>
);

var mockAsync = (data) =>
  jest.fn().mockImplementation(() => Promise.resolve(data ? data : { k: "v" }));

var mockAsyncRejection = () =>
  jest.fn().mockImplementation(() => Promise.reject());

var bar_servers = {
  "": {
    name: "",
    last_activity: "2020-12-07T20:58:02.437408Z",
    started: "2020-12-07T20:58:01.508266Z",
    pending: null,
    ready: false,
    state: { pid: 12345 },
    url: "/user/bar/",
    user_options: {},
    progress_url: "/hub/api/users/bar/progress",
  },
  servername: {
    name: "servername",
    last_activity: "2020-12-07T20:58:02.437408Z",
    started: "2020-12-07T20:58:01.508266Z",
    pending: null,
    ready: false,
    state: { pid: 12345 },
    url: "/user/bar/servername",
    user_options: {},
    progress_url: "/hub/api/users/bar/servername/progress",
  },
};

var mockAppState = () =>
  Object.assign({}, initialState, {
    user_data: [
      {
        kind: "user",
        name: "foo",
        admin: true,
        groups: [],
        server: "/user/foo/",
        pending: null,
        created: "2020-12-07T18:46:27.112695Z",
        last_activity: "2020-12-07T21:00:33.336354Z",
        servers: {
          "": {
            name: "",
            last_activity: "2020-12-07T20:58:02.437408Z",
            started: "2020-12-07T20:58:01.508266Z",
            pending: null,
            ready: true,
            state: { pid: 28085 },
            url: "/user/foo/",
            user_options: {},
            progress_url: "/hub/api/users/foo/server/progress",
          },
        },
      },
      {
        kind: "user",
        name: "bar",
        admin: false,
        groups: [],
        server: null,
        pending: null,
        created: "2020-12-07T18:46:27.115528Z",
        last_activity: "2020-12-07T20:43:51.013613Z",
        servers: bar_servers,
      },
    ],
    user_page: {
      offset: 0,
      limit: 2,
      total: 4,
      next: {
        offset: 2,
        limit: 2,
        url: "http://localhost:8000/hub/api/groups?offset=2&limit=2",
      },
    },
  });

var mockReducers = jest.fn((state, action) => {
  if (action.type === "USER_PAGE" && !action.value.data) {
    // no-op from mock, don't update state
    return state;
  }
  state = reducers(state, action);
  // mocked useSelector seems to cause a problem
  // this should get the right state back?
  // not sure
  // useSelector.mockImplementation((callback) => callback(state);
  return state;
});

let searchParams = new URLSearchParams();

beforeEach(() => {
  clock = sinon.useFakeTimers();
  useSelector.mockImplementation((callback) => {
    return callback(mockAppState());
  });
  searchParams = new URLSearchParams();

  useSearchParams.mockImplementation(() => [
    searchParams,
    (callback) => {
      searchParams = callback(searchParams);
    },
  ]);
});

afterEach(() => {
  useSearchParams.mockClear();
  useSelector.mockClear();
  mockReducers.mockClear();
  clock.restore();
});

test("Renders", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  expect(screen.getByTestId("container")).toBeVisible();
});

test("Renders users from props.user_data into table", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  let foo = screen.getByTestId("user-name-div-foo");
  let bar = screen.getByTestId("user-name-div-bar");
  let bar_server = screen.getByTestId("user-name-div-bar-servername");

  expect(foo).toBeVisible();
  expect(bar).toBeVisible();
  expect(bar_server).toBeVisible();
});

test("Renders correctly the status of a single-user server", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  let start_elems = screen.getAllByText("Start Server");
  expect(start_elems.length).toBe(Object.keys(bar_servers).length);
  start_elems.forEach((start) => {
    expect(start).toBeVisible();
  });

  let stop = screen.getByText("Stop Server");
  expect(stop).toBeVisible();
});

test("Renders spawn page link", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  for (let server in bar_servers) {
    let row = screen.getByTestId(`user-row-bar${server ? "-" + server : ""}`);
    let link = getByText(row, "Spawn Page").closest("a");
    let url = new URL(link.href);
    expect(url.pathname).toEqual("/spawn/bar" + (server ? "/" + server : ""));
  }
});

test("Invokes the startServer event on button click", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  let start_elems = screen.getAllByText("Start Server");
  expect(start_elems.length).toBe(Object.keys(bar_servers).length);

  await act(async () => {
    fireEvent.click(start_elems[0]);
  });

  expect(callbackSpy).toHaveBeenCalled();
});

test("Invokes the stopServer event on button click", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  let stop = screen.getByText("Stop Server");

  await act(async () => {
    fireEvent.click(stop);
  });

  expect(callbackSpy).toHaveBeenCalled();
});

test("Invokes the shutdownHub event on button click", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  let shutdown = screen.getByText("Shutdown Hub");

  await act(async () => {
    fireEvent.click(shutdown);
  });

  expect(callbackSpy).toHaveBeenCalled();
});

test("Sorts according to username", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  let handler = screen.getByTestId("user-sort");
  fireEvent.click(handler);

  let first = screen.getAllByTestId("user-row-name")[0];
  expect(first.textContent).toContain("bar");

  fireEvent.click(handler);

  first = screen.getAllByTestId("user-row-name")[0];
  expect(first.textContent).toContain("foo");
});

test("Sorts according to admin", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  let handler = screen.getByTestId("admin-sort");
  fireEvent.click(handler);

  let first = screen.getAllByTestId("user-row-admin")[0];
  expect(first.textContent).toBe("admin");

  fireEvent.click(handler);

  first = screen.getAllByTestId("user-row-admin")[0];
  expect(first.textContent).toBe("");
});

test("Sorts according to last activity", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  let handler = screen.getByTestId("last-activity-sort");
  fireEvent.click(handler);

  let first = screen.getAllByTestId("user-row-name")[0];
  expect(first.textContent).toContain("foo");

  fireEvent.click(handler);

  first = screen.getAllByTestId("user-row-name")[0];
  expect(first.textContent).toContain("bar");
});

test("Sorts according to server status (running/not running)", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  let handler = screen.getByTestId("running-status-sort");
  fireEvent.click(handler);

  let first = screen.getAllByTestId("user-row-name")[0];
  expect(first.textContent).toContain("foo");

  fireEvent.click(handler);

  first = screen.getAllByTestId("user-row-name")[0];
  expect(first.textContent).toContain("bar");
});

test("Shows server details with button click", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });
  let button = screen.getByTestId("foo-collapse-button");
  let collapse = screen.getByTestId("foo-collapse");
  let collapseBar = screen.getByTestId("bar-collapse");

  // expect().toBeVisible does not work here with collapse.
  expect(collapse).toHaveClass("collapse");
  expect(collapse).not.toHaveClass("show");
  expect(collapseBar).not.toHaveClass("show");

  await act(async () => {
    fireEvent.click(button);
    await clock.tick(400);
  });

  expect(collapse).toHaveClass("collapse show");
  expect(collapseBar).not.toHaveClass("show");

  await act(async () => {
    fireEvent.click(button);
    await clock.tick(400);
  });

  expect(collapse).toHaveClass("collapse");
  expect(collapse).not.toHaveClass("show");
  expect(collapseBar).not.toHaveClass("show");

  await act(async () => {
    fireEvent.click(button);
    await clock.tick(400);
  });

  expect(collapse).toHaveClass("collapse show");
  expect(collapseBar).not.toHaveClass("show");
});

test("Renders nothing if required data is not available", async () => {
  useSelector.mockImplementation((callback) => {
    return callback({});
  });

  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  let noShow = screen.getByTestId("no-show");

  expect(noShow).toBeVisible();
});

test("Shows a UI error dialogue when start all servers fails", async () => {
  let spy = mockAsync();
  let rejectSpy = mockAsyncRejection;

  await act(async () => {
    render(
      <Provider store={createStore(() => {}, {})}>
        <HashRouter>
          <CompatRouter>
            <Switch>
              <ServerDashboard
                updateUsers={spy}
                shutdownHub={spy}
                startServer={spy}
                stopServer={spy}
                startAll={rejectSpy}
                stopAll={spy}
              />
            </Switch>
          </CompatRouter>
        </HashRouter>
      </Provider>,
    );
  });

  let startAll = screen.getByTestId("start-all");

  await act(async () => {
    fireEvent.click(startAll);
  });

  let errorDialog = screen.getByText("Failed to start servers.");

  expect(errorDialog).toBeVisible();
});

test("Shows a UI error dialogue when stop all servers fails", async () => {
  let spy = mockAsync();
  let rejectSpy = mockAsyncRejection;

  await act(async () => {
    render(
      <Provider store={createStore(() => {}, {})}>
        <HashRouter>
          <CompatRouter>
            <Switch>
              <ServerDashboard
                updateUsers={spy}
                shutdownHub={spy}
                startServer={spy}
                stopServer={spy}
                startAll={spy}
                stopAll={rejectSpy}
              />
            </Switch>
          </CompatRouter>
        </HashRouter>
      </Provider>,
    );
  });

  let stopAll = screen.getByTestId("stop-all");

  await act(async () => {
    fireEvent.click(stopAll);
  });

  let errorDialog = screen.getByText("Failed to stop servers.");

  expect(errorDialog).toBeVisible();
});

test("Shows a UI error dialogue when start user server fails", async () => {
  let spy = mockAsync();
  let rejectSpy = mockAsyncRejection();

  await act(async () => {
    render(
      <Provider store={createStore(() => {}, {})}>
        <HashRouter>
          <CompatRouter>
            <Switch>
              <ServerDashboard
                updateUsers={spy}
                shutdownHub={spy}
                startServer={rejectSpy}
                stopServer={spy}
                startAll={spy}
                stopAll={spy}
              />
            </Switch>
          </CompatRouter>
        </HashRouter>
      </Provider>,
    );
  });

  let start_elems = screen.getAllByText("Start Server");
  expect(start_elems.length).toBe(Object.keys(bar_servers).length);

  await act(async () => {
    fireEvent.click(start_elems[0]);
  });

  let errorDialog = screen.getByText("Failed to start server.");

  expect(errorDialog).toBeVisible();
});

test("Shows a UI error dialogue when start user server returns an improper status code", async () => {
  let spy = mockAsync();
  let rejectSpy = mockAsync({ status: 403 });

  await act(async () => {
    render(
      <Provider store={createStore(() => {}, {})}>
        <HashRouter>
          <CompatRouter>
            <Switch>
              <ServerDashboard
                updateUsers={spy}
                shutdownHub={spy}
                startServer={rejectSpy}
                stopServer={spy}
                startAll={spy}
                stopAll={spy}
              />
            </Switch>
          </CompatRouter>
        </HashRouter>
      </Provider>,
    );
  });

  let start_elems = screen.getAllByText("Start Server");
  expect(start_elems.length).toBe(Object.keys(bar_servers).length);

  await act(async () => {
    fireEvent.click(start_elems[0]);
  });

  let errorDialog = screen.getByText("Failed to start server.");

  expect(errorDialog).toBeVisible();
});

test("Shows a UI error dialogue when stop user servers fails", async () => {
  let spy = mockAsync();
  let rejectSpy = mockAsyncRejection();

  await act(async () => {
    render(
      <Provider store={createStore(() => {}, {})}>
        <HashRouter>
          <CompatRouter>
            <Switch>
              <ServerDashboard
                updateUsers={spy}
                shutdownHub={spy}
                startServer={spy}
                stopServer={rejectSpy}
                startAll={spy}
                stopAll={spy}
              />
            </Switch>
          </CompatRouter>
        </HashRouter>
      </Provider>,
    );
  });

  let stop = screen.getByText("Stop Server");

  await act(async () => {
    fireEvent.click(stop);
  });

  let errorDialog = screen.getByText("Failed to stop server.");

  expect(errorDialog).toBeVisible();
});

test("Shows a UI error dialogue when stop user server returns an improper status code", async () => {
  let spy = mockAsync();
  let rejectSpy = mockAsync({ status: 403 });

  await act(async () => {
    render(
      <Provider store={createStore(() => {}, {})}>
        <HashRouter>
          <CompatRouter>
            <Switch>
              <ServerDashboard
                updateUsers={spy}
                shutdownHub={spy}
                startServer={spy}
                stopServer={rejectSpy}
                startAll={spy}
                stopAll={spy}
              />
            </Switch>
          </CompatRouter>
        </HashRouter>
      </Provider>,
    );
  });

  let stop = screen.getByText("Stop Server");

  await act(async () => {
    fireEvent.click(stop);
  });

  let errorDialog = screen.getByText("Failed to stop server.");

  expect(errorDialog).toBeVisible();
});

test("Search for user calls updateUsers with name filter", async () => {
  let spy = mockAsync();
  let mockUpdateUsers = jest.fn((offset, limit, name_filter) => {
    return Promise.resolve({
      items: [],
      _pagination: {
        offset: offset,
        limit: limit,
        total: offset + limit * 2,
        next: {
          offset: offset + limit,
          limit: limit,
        },
      },
    });
  });
  await act(async () => {
    render(
      <Provider store={createStore(mockReducers, mockAppState())}>
        <HashRouter>
          <CompatRouter>
            <Switch>
              <ServerDashboard
                updateUsers={mockUpdateUsers}
                shutdownHub={spy}
                startServer={spy}
                stopServer={spy}
                startAll={spy}
                stopAll={spy}
              />
            </Switch>
          </CompatRouter>
        </HashRouter>
      </Provider>,
    );
  });

  let search = screen.getByLabelText("user-search");

  expect(mockUpdateUsers.mock.calls).toHaveLength(1);

  userEvent.type(search, "a");
  expect(search.value).toEqual("a");
  await act(async () => {
    await clock.tick(400);
  });
  expect(searchParams.get("name_filter")).toEqual("a");
  // FIXME: useSelector mocks prevent updateUsers from being called
  // expect(mockUpdateUsers.mock.calls).toHaveLength(2);
  // expect(mockUpdateUsers).toBeCalledWith(0, 100, "a");
  userEvent.type(search, "b");
  expect(search.value).toEqual("ab");
  await act(async () => {
    jest.runAllTimers();
  });
  expect(searchParams.get("name_filter")).toEqual("ab");
  // expect(mockUpdateUsers).toBeCalledWith(0, 100, "ab");
});

test("Interacting with PaginationFooter causes state update and refresh via useEffect call", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  expect(callbackSpy).toBeCalledWith(0, 100, "");

  var n = 3;
  expect(searchParams.get("offset")).toEqual(null);
  expect(searchParams.get("limit")).toEqual(null);

  let next = screen.getByTestId("paginate-next");
  await act(async () => {
    fireEvent.click(next);
    await clock.tick(400);
  });

  expect(searchParams.get("offset")).toEqual("100");
  expect(searchParams.get("limit")).toEqual(null);

  // FIXME: should call updateUsers, does in reality.
  // tests don't reflect reality due to mocked state/useSelector
  // unclear how to fix this.
  // expect(callbackSpy.mock.calls).toHaveLength(2);
  // expect(callbackSpy).toHaveBeenCalledWith(2, 2, "");
});

test("Server delete button exists for named servers", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  for (let server in bar_servers) {
    if (server === "") {
      continue;
    }
    let row = screen.getByTestId(`user-row-bar-${server}`);
    let delete_button = getByText(row, "Delete Server");
    expect(delete_button).toBeEnabled();
  }
});

test("Start server and confirm pending state", async () => {
  let spy = mockAsync();

  let mockStartServer = jest.fn(() => {
    return new Promise(async (resolve) =>
      clock.setTimeout(() => {
        resolve({ status: 200 });
      }, 100),
    );
  });

  let mockUpdateUsers = jest.fn(() => Promise.resolve(mockAppState()));

  await act(async () => {
    render(
      <Provider store={createStore(mockReducers, {})}>
        <HashRouter>
          <CompatRouter>
            <Switch>
              <ServerDashboard
                updateUsers={mockUpdateUsers}
                shutdownHub={spy}
                startServer={mockStartServer}
                stopServer={spy}
                startAll={spy}
                stopAll={spy}
              />
            </Switch>
          </CompatRouter>
        </HashRouter>
      </Provider>,
    );
  });

  let actions = screen.getAllByTestId("user-row-server-activity")[1];
  let buttons = getAllByRole(actions, "button");

  expect(buttons.length).toBe(2);
  expect(buttons[0].textContent).toBe("Start Server");
  expect(buttons[1].textContent).toBe("Spawn Page");

  await act(async () => {
    fireEvent.click(buttons[0]);
  });
  expect(mockUpdateUsers.mock.calls).toHaveLength(1);

  expect(buttons.length).toBe(2);
  expect(buttons[0].textContent).toBe("Start Server");
  expect(buttons[0]).toBeDisabled();
  expect(buttons[1].textContent).toBe("Spawn Page");
  expect(buttons[1]).toBeEnabled();

  await act(async () => {
    await clock.tick(100);
  });
  expect(mockUpdateUsers.mock.calls).toHaveLength(2);
});
