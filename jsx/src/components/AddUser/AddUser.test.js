import React from "react";
import "@testing-library/jest-dom";
import { act } from "react-dom/test-utils";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider, useDispatch, useSelector } from "react-redux";
import { createStore } from "redux";
import { HashRouter } from "react-router-dom";
// eslint-disable-next-line
import regeneratorRuntime from "regenerator-runtime";

import AddUser from "./AddUser";

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useDispatch: jest.fn(),
  useSelector: jest.fn(),
}));

var mockAsync = (result) =>
  jest.fn().mockImplementation(() => Promise.resolve(result));

var mockAsyncRejection = () =>
  jest.fn().mockImplementation(() => Promise.reject());

var addUserJsx = (spy, spy2, spy3) => (
  <Provider store={createStore(() => {}, {})}>
    <HashRouter>
      <AddUser
        addUsers={spy}
        updateUsers={spy3 || spy2 || spy}
        history={{ push: () => {} }}
      />
    </HashRouter>
  </Provider>
);

var mockAppState = () => ({
  limit: 3,
});

beforeEach(() => {
  useDispatch.mockImplementation(() => {
    return () => {};
  });
  useSelector.mockImplementation((callback) => {
    return callback(mockAppState());
  });
});

afterEach(() => {
  useDispatch.mockClear();
});

test("Renders", async () => {
  await act(async () => {
    render(addUserJsx());
  });
  expect(screen.getByTestId("container")).toBeVisible();
});

test("Removes users when they fail Regex", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(addUserJsx(callbackSpy));
  });

  let textarea = screen.getByTestId("user-textarea");
  let submit = screen.getByTestId("submit");

  fireEvent.blur(textarea, { target: { value: "foo \n bar\na@b.co\n  \n\n" } });
  await act(async () => {
    fireEvent.click(submit);
  });

  expect(callbackSpy).toHaveBeenCalledWith(["foo", "bar", "a@b.co"], false);
});

test("Correctly submits admin", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(addUserJsx(callbackSpy));
  });

  let textarea = screen.getByTestId("user-textarea");
  let submit = screen.getByTestId("submit");
  let check = screen.getByTestId("check");

  userEvent.click(check);
  fireEvent.blur(textarea, { target: { value: "foo" } });
  await act(async () => {
    fireEvent.click(submit);
  });

  expect(callbackSpy).toHaveBeenCalledWith(["foo"], true);
});

test("Shows a UI error dialogue when user creation fails", async () => {
  let callbackSpy = mockAsyncRejection();

  await act(async () => {
    render(addUserJsx(callbackSpy));
  });

  let submit = screen.getByTestId("submit");

  await act(async () => {
    fireEvent.click(submit);
  });

  let errorDialog = screen.getByText("Failed to create user.");

  expect(errorDialog).toBeVisible();
  expect(callbackSpy).toHaveBeenCalled();
});

test("Shows a more specific UI error dialogue when user creation returns an improper status code", async () => {
  let callbackSpy = mockAsync({ status: 409 });

  await act(async () => {
    render(addUserJsx(callbackSpy));
  });

  let submit = screen.getByTestId("submit");

  await act(async () => {
    fireEvent.click(submit);
  });

  let errorDialog = screen.getByText(
    "Failed to create user. User already exists.",
  );

  expect(errorDialog).toBeVisible();
  expect(callbackSpy).toHaveBeenCalled();
});
