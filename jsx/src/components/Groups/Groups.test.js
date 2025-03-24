import React, { act } from "react";
import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider, useSelector } from "react-redux";
import { createStore } from "redux";
import { HashRouter, useSearchParams } from "react-router";
// eslint-disable-next-line
import regeneratorRuntime from "regenerator-runtime";

import { initialState, reducers } from "../../Store";
import Groups from "./Groups";

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useSelector: jest.fn(),
}));

jest.mock("react-router", () => ({
  ...jest.requireActual("react-router"),
  useSearchParams: jest.fn(),
}));

var mockAsync = () =>
  jest.fn().mockImplementation(() => Promise.resolve({ key: "value" }));

var groupsJsx = (callbackSpy) => (
  <Provider store={createStore(mockReducers, mockAppState())}>
    <HashRouter>
      <Groups updateGroups={callbackSpy} />
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
    },
  });

var mockUpdateGroups = () => {
  const state = mockAppState();
  return jest.fn().mockImplementation((offset, limit) =>
    Promise.resolve({
      items: state.groups_data.slice(0, limit),
      _pagination: {
        offset: offset,
        limit: limit || 2,
        total: state.groups_page.total,
      },
    }),
  );
};

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
  useSelector.mockClear();
  mockReducers.mockClear();
  useSearchParams.mockClear();
  jest.runAllTimers();
});

test("Renders", async () => {
  let callbackSpy = mockUpdateGroups();

  await act(async () => {
    render(groupsJsx(callbackSpy));
  });

  expect(screen.getByTestId("container")).toBeVisible();
});

test("Renders groups_data prop into links", async () => {
  let callbackSpy = mockUpdateGroups();

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

  let callbackSpy = mockUpdateGroups();

  await act(async () => {
    render(groupsJsx(callbackSpy));
  });

  let noShow = screen.getByTestId("no-show");
  expect(noShow).toBeVisible();
});

test("Interacting with PaginationFooter causes page refresh", async () => {
  let updateGroupsSpy = mockUpdateGroups();
  await act(async () => {
    render(groupsJsx(updateGroupsSpy));
  });

  expect(updateGroupsSpy).toBeCalledWith(0, 2);

  var lastState =
    mockReducers.mock.results[mockReducers.mock.results.length - 1].value;
  expect(lastState.groups_page.offset).toEqual(0);
  expect(lastState.groups_page.limit).toEqual(2);
  expect(searchParams.get("offset")).toEqual(null);

  let next = screen.getByTestId("paginate-next");
  await act(async () => {
    await fireEvent.click(next);
  });
  expect(searchParams.get("offset")).toEqual("2");
  // FIXME: useSelector mocks prevent updateGroups from being called
  // expect(updateGroupsSpy).toBeCalledWith(2, 2);
});
