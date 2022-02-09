import React from "react";
import "@testing-library/jest-dom";
import { act } from "react-dom/test-utils";
import { render, screen } from "@testing-library/react";
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
  user_data: JSON.parse(
    '[{"kind":"user","name":"foo","admin":true,"groups":[],"server":"/user/foo/","pending":null,"created":"2020-12-07T18:46:27.112695Z","last_activity":"2020-12-07T21:00:33.336354Z","servers":{"":{"name":"","last_activity":"2020-12-07T20:58:02.437408Z","started":"2020-12-07T20:58:01.508266Z","pending":null,"ready":true,"state":{"pid":28085},"url":"/user/foo/","user_options":{},"progress_url":"/hub/api/users/foo/server/progress"}}},{"kind":"user","name":"bar","admin":false,"groups":[],"server":null,"pending":null,"created":"2020-12-07T18:46:27.115528Z","last_activity":"2020-12-07T20:43:51.013613Z","servers":{}}]'
  ),
  groups_data: JSON.parse(
    '[{"kind":"group","name":"testgroup","users":[]}, {"kind":"group","name":"testgroup2","users":["foo", "bar"]}]'
  ),
  limit: 10,
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
