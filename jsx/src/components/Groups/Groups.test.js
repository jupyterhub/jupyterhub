import React from "react";
import "@testing-library/jest-dom";
import { act } from "react-dom/test-utils";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider, useDispatch, useSelector } from "react-redux";
import { createStore } from "redux";
import { HashRouter } from "react-router-dom";
// eslint-disable-next-line
import regeneratorRuntime from "regenerator-runtime";

import { initialState, reducers } from "../../Store";
import Groups from "./Groups";

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useSelector: jest.fn(),
}));

var mockAsync = () =>
  jest.fn().mockImplementation(() => Promise.resolve({ key: "value" }));

var groupsJsx = (callbackSpy) => (
  <Provider store={createStore(mockReducers, mockAppState())}>
    <HashRouter>
      <Groups location={{ search: "0" }} updateGroups={callbackSpy} />
    </HashRouter>
  </Provider>
);

var mockReducers = jest.fn((state, action) => {
  if (action.type === "GROUPS_PAGE" && !action.value.data) {
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

var mockAppState = () =>
  Object.assign({}, initialState, {
    groups_data: [
      { kind: "group", name: "testgroup", users: [] },
      { kind: "group", name: "testgroup2", users: ["foo", "bar"] },
    ],
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
});

afterEach(() => {
  useSelector.mockClear();
  mockReducers.mockClear();
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

  var lastState =
    mockReducers.mock.results[mockReducers.mock.results.length - 1].value;
  expect(lastState.groups_page.offset).toEqual(0);
  expect(lastState.groups_page.limit).toEqual(2);

  let next = screen.getByTestId("paginate-next");
  fireEvent.click(next);

  lastState =
    mockReducers.mock.results[mockReducers.mock.results.length - 1].value;
  expect(lastState.groups_page.offset).toEqual(2);
  expect(lastState.groups_page.limit).toEqual(2);

  // FIXME: mocked useSelector, state seem to prevent updateGroups from being called
  // making the test environment not representative
  // expect(callbackSpy).toHaveBeenCalledWith(2, 2);
});
