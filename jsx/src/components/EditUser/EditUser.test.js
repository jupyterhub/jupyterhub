import React from "react";
import "@testing-library/jest-dom";
import { act } from "react-dom/test-utils";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider, useDispatch, useSelector } from "react-redux";
import { createStore } from "redux";
import { HashRouter } from "react-router-dom";
// eslint-disable-next-line
import regeneratorRuntime from "regenerator-runtime";

import EditUser from "./EditUser";

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useDispatch: jest.fn(),
  useSelector: jest.fn(),
}));

var mockAsync = (data) =>
  jest.fn().mockImplementation(() => Promise.resolve(data));

var mockAsyncRejection = () =>
  jest.fn().mockImplementation(() => Promise.reject());

var editUserJsx = (callbackSpy, empty) => (
  <Provider store={createStore(() => {}, {})}>
    <HashRouter>
      <EditUser
        location={empty ? {} : { state: { username: "foo", has_admin: false } }}
        deleteUser={callbackSpy}
        editUser={callbackSpy}
        updateUsers={callbackSpy}
        history={{ push: () => {} }}
        noChangeEvent={callbackSpy}
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
  let callbackSpy = mockAsync({ key: "value", status: 200 });

  await act(async () => {
    render(editUserJsx(callbackSpy));
  });

  expect(screen.getByTestId("container")).toBeVisible();
});

test("Calls the delete user function when the button is pressed", async () => {
  let callbackSpy = mockAsync({ key: "value", status: 200 });

  await act(async () => {
    render(editUserJsx(callbackSpy));
  });

  let deleteUser = screen.getByTestId("delete-user");

  await act(async () => {
    fireEvent.click(deleteUser);
  });

  expect(callbackSpy).toHaveBeenCalled();
});

test("Submits the edits when the button is pressed", async () => {
  let callbackSpy = mockAsync({ key: "value", status: 200 });

  await act(async () => {
    render(editUserJsx(callbackSpy));
  });

  let submit = screen.getByTestId("submit");
  await act(async () => {
    fireEvent.click(submit);
  });

  expect(callbackSpy).toHaveBeenCalled();
});

test("Shows a UI error dialogue when user edit fails", async () => {
  let callbackSpy = mockAsyncRejection();

  await act(async () => {
    render(editUserJsx(callbackSpy));
  });

  let submit = screen.getByTestId("submit");
  let usernameInput = screen.getByTestId("edit-username-input");

  fireEvent.blur(usernameInput, { target: { value: "whatever" } });
  await act(async () => {
    fireEvent.click(submit);
  });

  let errorDialog = screen.getByText("Failed to edit user.");

  expect(errorDialog).toBeVisible();
  expect(callbackSpy).toHaveBeenCalled();
});

test("Shows a UI error dialogue when user edit returns an improper status code", async () => {
  let callbackSpy = mockAsync({ status: 409 });

  await act(async () => {
    render(editUserJsx(callbackSpy));
  });

  let submit = screen.getByTestId("submit");
  let usernameInput = screen.getByTestId("edit-username-input");

  fireEvent.blur(usernameInput, { target: { value: "whatever" } });
  await act(async () => {
    fireEvent.click(submit);
  });

  let errorDialog = screen.getByText("Failed to edit user.");

  expect(errorDialog).toBeVisible();
  expect(callbackSpy).toHaveBeenCalled();
});
