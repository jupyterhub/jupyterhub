import React from "react";
import "@testing-library/jest-dom";
import { act } from "react-dom/test-utils";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider, useDispatch, useSelector } from "react-redux";
import { createStore } from "redux";
import { HashRouter } from "react-router-dom";
// eslint-disable-next-line
import regeneratorRuntime from "regenerator-runtime";

import Groups from "./Groups";

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useSelector: jest.fn(),
  useDispatch: jest.fn(),
}));

var mockAsync = () =>
  jest.fn().mockImplementation(() => Promise.resolve({ key: "value" }));

var groupsJsx = (callbackSpy) => (
  <Provider store={createStore(() => {}, {})}>
    <HashRouter>
      <Groups location={{ search: "0" }} updateGroups={callbackSpy} />
    </HashRouter>
  </Provider>
);

var mockAppState = () => ({
  groups_data: JSON.parse(
    '[{"kind":"group","name":"testgroup","users":[]}, {"kind":"group","name":"testgroup2","users":["foo", "bar"]}]'
  ),
  groups_page: {
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

beforeEach(() => {
  useSelector.mockImplementation((callback) => {
    return callback(mockAppState());
  });
  useDispatch.mockImplementation(() => {
    return () => {};
  });
});

afterEach(() => {
  useSelector.mockClear();
});

test("Renders", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(groupsJsx(callbackSpy));
  });

  expect(screen.getByTestId("container")).toBeVisible();
});

test("Renders groups_data prop into links", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(groupsJsx(callbackSpy));
  });

  let testgroup = screen.getByText("testgroup");
  let testgroup2 = screen.getByText("testgroup2");

  expect(testgroup).toBeVisible();
  expect(testgroup2).toBeVisible();
});

test("Renders nothing if required data is not available", async () => {
  useSelector.mockImplementation((callback) => {
    return callback({});
  });

  let callbackSpy = mockAsync();

  await act(async () => {
    render(groupsJsx(callbackSpy));
  });

  let noShow = screen.getByTestId("no-show");
  expect(noShow).toBeVisible();
});

test("Interacting with PaginationFooter causes state update and refresh via useEffect call", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(groupsJsx(callbackSpy));
  });

  expect(callbackSpy).toBeCalledWith(0, 2);

  let next = screen.getByTestId("paginate-next");
  fireEvent.click(next);

  expect(callbackSpy).toHaveBeenCalledWith(2, 2);
});
