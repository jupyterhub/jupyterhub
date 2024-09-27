import React, { act } from "react";
import { withProps } from "recompose";
import "@testing-library/jest-dom";
import userEvent from "@testing-library/user-event";
import {
  render,
  screen,
  fireEvent,
  getByText,
  getAllByRole,
} from "@testing-library/react";
import { HashRouter, Routes, Route, useSearchParams } from "react-router-dom";
// import { CompatRouter,  } from "react-router-dom-v5-compat";
import { Provider, useSelector } from "react-redux";
import { createStore } from "redux";
// eslint-disable-next-line
import regeneratorRuntime from "regenerator-runtime";

import ServerDashboard from "./ServerDashboard";
import { initialState, reducers } from "../../Store";

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useSelector: jest.fn(),
}));
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useSearchParams: jest.fn(),
}));

const serverDashboardJsx = (props) => {
  // create mock ServerDashboard
  // spies is a dict of properties to mock in
  // any API calls that will fire during the test should be mocked
  props = props || {};
  if (!props.updateUsers) {
    props.updateUsers = mockUpdateUsers;
  }
  return (
    <Provider store={createStore(mockReducers, mockAppState())}>
      <HashRouter>
        <Routes>
          <Route path="/" element={withProps(props)(ServerDashboard)()} />
        </Routes>
      </HashRouter>
    </Provider>
  );
};

var mockAsync = (data) =>
  jest.fn().mockImplementation(() => Promise.resolve(data ? data : { k: "v" }));

var mockAsyncRejection = () =>
  jest.fn().mockImplementation(() => Promise.reject());

const defaultUpdateUsersParams = {
  offset: 0,
  limit: 2,
  name_filter: "",
  sort: "id",
  state: "",
};

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

/* create new user models */
const newUser = (name) => {
  return {
    kind: "user",
    name: name,
    admin: false,
    groups: [],
    server: `/user/${name}`,
    created: "2020-12-07T18:46:27.112695Z",
    last_activity: "2020-12-07T21:00:33.336354Z",
    servers: {},
  };
};

const allUsers = [
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
];

for (var i = 2; i < 10; i++) {
  allUsers.push(newUser(`test-${i}`));
}

var mockAppState = () =>
  Object.assign({}, initialState, {
    user_data: allUsers.slice(0, 2),
    user_page: {
      offset: 0,
      limit: 2,
      total: 4,
      next: {
        offset: 2,
        limit: 2,
        url: "http://localhost:8000/hub/api/users?offset=2&limit=2",
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

let mockUpdateUsers = jest.fn(({ offset, limit, sort, name_filter, state }) => {
  /* mock updating users 
  
  this has tom implement the server-side filtering, sorting, etc.
  (at least whatever we want to test of it)
  */
  let matchingUsers = allUsers;
  if (state === "active") {
    // only first user is active
    matchingUsers = allUsers.slice(0, 1);
  }
  if (name_filter) {
    matchingUsers = matchingUsers.filter((user) =>
      user.name.startsWith(name_filter),
    );
  }

  const total = matchingUsers.length;
  const items = matchingUsers.slice(offset, offset + limit);

  return Promise.resolve({
    items: items,
    _pagination: {
      offset: offset,
      limit: limit,
      total: total,
      next: {
        offset: offset + limit,
        limit: limit,
      },
    },
  });
});

let searchParams = new URLSearchParams();

beforeEach(() => {
  useSelector.mockImplementation((callback) => {
    return callback(mockAppState());
  });
  searchParams = new URLSearchParams();
  searchParams.set("limit", "2");

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
  mockUpdateUsers.mockClear();
  jest.runAllTimers();
});

test("Renders", async () => {
  await act(async () => {
    render(serverDashboardJsx());
  });

  expect(screen.getByTestId("container")).toBeVisible();
});

test("Renders users from props.user_data into table", async () => {
  await act(async () => {
    render(serverDashboardJsx());
  });

  let foo = screen.getByTestId("user-name-div-foo");
  let bar = screen.getByTestId("user-name-div-bar");
  let bar_server = screen.getByTestId("user-name-div-bar-servername");

  expect(foo).toBeVisible();
  expect(bar).toBeVisible();
  expect(bar_server).toBeVisible();
});

test("Renders correctly the status of a single-user server", async () => {
  await act(async () => {
    render(serverDashboardJsx());
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
  await act(async () => {
    render(serverDashboardJsx());
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
    render(serverDashboardJsx({ startServer: callbackSpy }));
  });

  let start_elems = screen.getAllByText("Start Server");
  expect(start_elems.length).toBe(Object.keys(bar_servers).length);

  await act(async () => {
    await fireEvent.click(start_elems[0]);
  });

  expect(callbackSpy).toHaveBeenCalled();
});

test("Invokes the stopServer event on button click", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx({ stopServer: callbackSpy }));
  });

  let stop = screen.getByText("Stop Server");

  await act(async () => {
    await fireEvent.click(stop);
  });

  expect(callbackSpy).toHaveBeenCalled();
});

test("Invokes the shutdownHub event on button click", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx({ shutdownHub: callbackSpy }));
  });

  let shutdown = screen.getByText("Shutdown Hub");

  await act(async () => {
    await fireEvent.click(shutdown);
  });

  expect(callbackSpy).toHaveBeenCalled();
});

test("Sorts according to username", async () => {
  let rerender;
  const testId = "user-sort";
  await act(async () => {
    rerender = render(serverDashboardJsx()).rerender;
  });

  expect(searchParams.get("sort")).toEqual(null);
  let handler = screen.getByTestId(testId);
  await fireEvent.click(handler);
  expect(searchParams.get("sort")).toEqual("name");

  await act(async () => {
    rerender(serverDashboardJsx());
    handler = screen.getByTestId(testId);
  });

  await fireEvent.click(handler);
  expect(searchParams.get("sort")).toEqual("-name");

  await act(async () => {
    rerender(serverDashboardJsx());
    handler = screen.getByTestId(testId);
  });

  await fireEvent.click(handler);
  expect(searchParams.get("sort")).toEqual("name");
});

test("Sorts according to last activity", async () => {
  let rerender;
  const testId = "last-activity-sort";
  await act(async () => {
    rerender = render(serverDashboardJsx()).rerender;
  });

  expect(searchParams.get("sort")).toEqual(null);
  let handler = screen.getByTestId(testId);
  await fireEvent.click(handler);
  expect(searchParams.get("sort")).toEqual("last_activity");

  await act(async () => {
    rerender(serverDashboardJsx());
    handler = screen.getByTestId(testId);
  });

  await fireEvent.click(handler);
  expect(searchParams.get("sort")).toEqual("-last_activity");

  await act(async () => {
    rerender(serverDashboardJsx());
    handler = screen.getByTestId(testId);
  });

  await fireEvent.click(handler);
  expect(searchParams.get("sort")).toEqual("last_activity");
});

test("Filter according to server status (running/not running)", async () => {
  let rerender;
  await act(async () => {
    rerender = render(serverDashboardJsx()).rerender;
  });
  const label = "only active servers";
  let handler = screen.getByLabelText(label);
  expect(handler.checked).toEqual(false);
  await fireEvent.click(handler);

  // FIXME: need to force a rerender to get updated checkbox
  // I don't think this should be required
  await act(async () => {
    rerender(serverDashboardJsx());
    handler = screen.getByLabelText(label);
  });
  expect(searchParams.get("state")).toEqual("active");
  expect(handler.checked).toEqual(true);

  await fireEvent.click(handler);

  await act(async () => {
    rerender(serverDashboardJsx());
    handler = screen.getByLabelText(label);
  });
  handler = screen.getByLabelText(label);
  expect(handler.checked).toEqual(false);
  expect(searchParams.get("state")).toEqual(null);
});

test("Shows server details with button click", async () => {
  await act(async () => {
    render(serverDashboardJsx());
  });
  let button = screen.getByTestId("foo-collapse-button");
  let collapse = screen.getByTestId("foo-collapse");
  let collapseBar = screen.getByTestId("bar-collapse");

  // expect().toBeVisible does not work here with collapse.
  expect(collapse).toHaveClass("collapse");
  expect(collapse).not.toHaveClass("show");
  expect(collapseBar).not.toHaveClass("show");
  await fireEvent.click(button);
  await act(async () => {
    jest.runAllTimers();
  });
  expect(collapse).toHaveClass("collapse show");
  expect(collapseBar).not.toHaveClass("show");
  await fireEvent.click(button);
  await act(async () => {
    jest.runAllTimers();
  });

  expect(collapse).toHaveClass("collapse");
  expect(collapse).not.toHaveClass("show");
  expect(collapseBar).not.toHaveClass("show");

  await fireEvent.click(button);
  await act(async () => {
    jest.runAllTimers();
  });

  expect(collapse).toHaveClass("collapse show");
  expect(collapseBar).not.toHaveClass("show");
});

test("Renders nothing if required data is not available", async () => {
  useSelector.mockImplementation((callback) => {
    return callback({});
  });

  await act(async () => {
    render(serverDashboardJsx());
  });

  let noShow = screen.getByTestId("no-show");

  expect(noShow).toBeVisible();
});

test("Shows a UI error dialogue when start all servers fails", async () => {
  await act(async () => {
    render(serverDashboardJsx({ startAll: mockAsyncRejection }));
  });

  let startAll = screen.getByTestId("start-all");

  await act(async () => {
    await fireEvent.click(startAll);
  });

  let errorDialog = screen.getByText("Failed to start servers.");

  expect(errorDialog).toBeVisible();
});

test("Shows a UI error dialogue when stop all servers fails", async () => {
  await act(async () => {
    render(serverDashboardJsx({ stopAll: mockAsyncRejection }));
  });

  let stopAll = screen.getByTestId("stop-all");

  await act(async () => {
    await fireEvent.click(stopAll);
  });

  let errorDialog = screen.getByText("Failed to stop servers.");

  expect(errorDialog).toBeVisible();
});

test("Shows a UI error dialogue when start user server fails", async () => {
  await act(async () => {
    render(serverDashboardJsx({ startServer: mockAsyncRejection() }));
  });

  let start_elems = screen.getAllByText("Start Server");
  expect(start_elems.length).toBe(Object.keys(bar_servers).length);

  await act(async () => {
    await fireEvent.click(start_elems[0]);
  });

  let errorDialog = screen.getByText("Failed to start server.");

  expect(errorDialog).toBeVisible();
});

test("Shows a UI error dialogue when start user server returns an improper status code", async () => {
  let rejectSpy = mockAsync({ status: 403 });
  await act(async () => {
    render(serverDashboardJsx({ startServer: rejectSpy }));
  });

  let start_elems = screen.getAllByText("Start Server");
  expect(start_elems.length).toBe(Object.keys(bar_servers).length);

  await act(async () => {
    await fireEvent.click(start_elems[0]);
  });

  let errorDialog = screen.getByText("Failed to start server.");

  expect(errorDialog).toBeVisible();
});

test("Shows a UI error dialogue when stop user servers fails", async () => {
  let spy = mockAsync();
  let rejectSpy = mockAsyncRejection();

  await act(async () => {
    render(serverDashboardJsx({ stopServer: rejectSpy }));
  });

  let stop = screen.getByText("Stop Server");

  await act(async () => {
    await fireEvent.click(stop);
  });

  let errorDialog = screen.getByText("Failed to stop server.");

  expect(errorDialog).toBeVisible();
});

test("Shows a UI error dialogue when stop user server returns an improper status code", async () => {
  let spy = mockAsync();
  let rejectSpy = mockAsync({ status: 403 });

  await act(async () => {
    render(serverDashboardJsx({ stopServer: rejectSpy }));
  });

  let stop = screen.getByText("Stop Server");

  await act(async () => {
    await fireEvent.click(stop);
  });

  let errorDialog = screen.getByText("Failed to stop server.");

  expect(errorDialog).toBeVisible();
});

test("Search for user calls updateUsers with name filter", async () => {
  let spy = mockAsync();
  await act(async () => {
    searchParams.set("offset", "2");
    render(serverDashboardJsx());
  });

  const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
  let search = screen.getByLabelText("user-search");

  expect(mockUpdateUsers.mock.calls).toHaveLength(1);

  expect(searchParams.get("offset")).toEqual("2");
  await user.type(search, "a");
  expect(search.value).toEqual("a");
  await act(async () => {
    jest.runAllTimers();
  });
  expect(searchParams.get("name_filter")).toEqual("a");
  expect(searchParams.get("offset")).toEqual(null);
  // FIXME: useSelector mocks prevent updateUsers from being called
  // expect(mockUpdateUsers.mock.calls).toHaveLength(2);
  // expect(mockUpdateUsers).toBeCalledWith(0, 100, "a");
  await user.type(search, "b");
  expect(search.value).toEqual("ab");
  await act(async () => {
    jest.runAllTimers();
  });
  expect(searchParams.get("name_filter")).toEqual("ab");
  // expect(mockUpdateUsers).toBeCalledWith(0, 100, "ab");
});

test("Interacting with PaginationFooter requests page update", async () => {
  await act(async () => {
    render(serverDashboardJsx());
  });

  expect(mockUpdateUsers).toBeCalledWith(defaultUpdateUsersParams);

  var n = 3;
  expect(searchParams.get("offset")).toEqual(null);
  expect(searchParams.get("limit")).toEqual("2");

  let next = screen.getByTestId("paginate-next");
  await act(async () => {
    fireEvent.click(next);
    jest.runAllTimers();
  });

  expect(mockUpdateUsers).toBeCalledWith({
    ...defaultUpdateUsersParams,
    offset: 2,
  });
});

test("Server delete button exists for named servers", async () => {
  await act(async () => {
    render(serverDashboardJsx());
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
  let mockStartServer = jest.fn(() => {
    return new Promise(async (resolve) =>
      setTimeout(() => {
        resolve({ status: 200 });
      }, 100),
    );
  });

  await act(async () => {
    render(
      serverDashboardJsx({
        startServer: mockStartServer,
      }),
    );
  });

  let actions = screen.getAllByTestId("user-row-server-activity")[1];
  let buttons = getAllByRole(actions, "button");

  expect(buttons.length).toBe(3);
  expect(buttons[0].textContent).toBe("Start Server");
  expect(buttons[1].textContent).toBe("Spawn Page");
  expect(buttons[2].textContent).toBe("Edit User");

  await act(async () => {
    await fireEvent.click(buttons[0]);
  });
  expect(mockUpdateUsers.mock.calls).toHaveLength(1);

  expect(buttons.length).toBe(3);
  expect(buttons[0].textContent).toBe("Start Server");
  expect(buttons[0]).toBeDisabled();
  expect(buttons[1].textContent).toBe("Spawn Page");
  expect(buttons[1]).toBeEnabled();

  await act(async () => {
    jest.runAllTimers();
  });
  expect(mockUpdateUsers.mock.calls).toHaveLength(2);
});
