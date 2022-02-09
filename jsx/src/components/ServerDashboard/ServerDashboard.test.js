import React from "react";
import "@testing-library/jest-dom";
import { act } from "react-dom/test-utils";
import { render, screen, fireEvent } from "@testing-library/react";
import { HashRouter, Switch } from "react-router-dom";
import { Provider, useSelector } from "react-redux";
import { createStore } from "redux";
// eslint-disable-next-line
import regeneratorRuntime from "regenerator-runtime";

import ServerDashboard from "./ServerDashboard";

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useSelector: jest.fn(),
}));

var serverDashboardJsx = (spy) => (
  <Provider store={createStore(() => {}, {})}>
    <HashRouter>
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
    </HashRouter>
  </Provider>
);

var mockAsync = (data) =>
  jest.fn().mockImplementation(() => Promise.resolve(data ? data : { k: "v" }));

var mockAsyncRejection = () =>
  jest.fn().mockImplementation(() => Promise.reject());

var mockAppState = () => ({
  user_data: JSON.parse(
    '[{"kind":"user","name":"foo","admin":true,"groups":[],"server":"/user/foo/","pending":null,"created":"2020-12-07T18:46:27.112695Z","last_activity":"2020-12-07T21:00:33.336354Z","servers":{"":{"name":"","last_activity":"2020-12-07T20:58:02.437408Z","started":"2020-12-07T20:58:01.508266Z","pending":null,"ready":true,"state":{"pid":28085},"url":"/user/foo/","user_options":{},"progress_url":"/hub/api/users/foo/server/progress"}}},{"kind":"user","name":"bar","admin":false,"groups":[],"server":null,"pending":null,"created":"2020-12-07T18:46:27.115528Z","last_activity":"2020-12-07T20:43:51.013613Z","servers":{}}]'
  ),
});

beforeEach(() => {
  useSelector.mockImplementation((callback) => {
    return callback(mockAppState());
  });
});

afterEach(() => {
  useSelector.mockClear();
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

  let foo = screen.getByText("foo");
  let bar = screen.getByText("bar");

  expect(foo).toBeVisible();
  expect(bar).toBeVisible();
});

test("Renders correctly the status of a single-user server", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  let start = screen.getByText("Start Server");
  let stop = screen.getByText("Stop Server");

  expect(start).toBeVisible();
  expect(stop).toBeVisible();
});

test("Invokes the startServer event on button click", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  let start = screen.getByText("Start Server");

  await act(async () => {
    fireEvent.click(start);
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
  expect(first.textContent).toBe("bar");

  fireEvent.click(handler);

  first = screen.getAllByTestId("user-row-name")[0];
  expect(first.textContent).toBe("foo");
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
  expect(first.textContent).toBe("foo");

  fireEvent.click(handler);

  first = screen.getAllByTestId("user-row-name")[0];
  expect(first.textContent).toBe("bar");
});

test("Sorts according to server status (running/not running)", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(serverDashboardJsx(callbackSpy));
  });

  let handler = screen.getByTestId("running-status-sort");
  fireEvent.click(handler);

  let first = screen.getAllByTestId("user-row-name")[0];
  expect(first.textContent).toBe("foo");

  fireEvent.click(handler);

  first = screen.getAllByTestId("user-row-name")[0];
  expect(first.textContent).toBe("bar");
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
        </HashRouter>
      </Provider>
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
        </HashRouter>
      </Provider>
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
        </HashRouter>
      </Provider>
    );
  });

  let start = screen.getByText("Start Server");

  await act(async () => {
    fireEvent.click(start);
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
        </HashRouter>
      </Provider>
    );
  });

  let start = screen.getByText("Start Server");

  await act(async () => {
    fireEvent.click(start);
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
        </HashRouter>
      </Provider>
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
        </HashRouter>
      </Provider>
    );
  });

  let stop = screen.getByText("Stop Server");

  await act(async () => {
    fireEvent.click(stop);
  });

  let errorDialog = screen.getByText("Failed to stop server.");

  expect(errorDialog).toBeVisible();
});
