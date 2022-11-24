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
import CreateGroup from "./CreateGroup";

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useDispatch: jest.fn(),
  useSelector: jest.fn(),
}));

var mockAsync = (result) =>
  jest.fn().mockImplementation(() => Promise.resolve(result));

var mockAsyncRejection = () =>
  jest.fn().mockImplementation(() => Promise.reject());

var createGroupJsx = (callbackSpy) => (
  <Provider store={createStore(() => {}, {})}>
    <HashRouter>
      <CreateGroup
        createGroup={callbackSpy}
        updateGroups={callbackSpy}
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
    return () => () => {};
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
    render(createGroupJsx());
  });
  expect(screen.getByTestId("container")).toBeVisible();
});

test("Calls createGroup on submit", async () => {
  let callbackSpy = mockAsync({ status: 200 });

  await act(async () => {
    render(createGroupJsx(callbackSpy));
  });

  let input = screen.getByTestId("group-input");
  let submit = screen.getByTestId("submit");

  userEvent.type(input, "groupname");
  await act(async () => fireEvent.click(submit));

  expect(callbackSpy).toHaveBeenNthCalledWith(1, "groupname");
});

test("Shows a UI error dialogue when group creation fails", async () => {
  let callbackSpy = mockAsyncRejection();

  await act(async () => {
    render(createGroupJsx(callbackSpy));
  });

  let submit = screen.getByTestId("submit");

  await act(async () => {
    fireEvent.click(submit);
  });

  let errorDialog = screen.getByText("Failed to create group.");

  expect(errorDialog).toBeVisible();
  expect(callbackSpy).toHaveBeenCalled();
});

test("Shows a more specific UI error dialogue when user creation returns an improper status code", async () => {
  let callbackSpy = mockAsync({ status: 409 });

  await act(async () => {
    render(createGroupJsx(callbackSpy));
  });

  let submit = screen.getByTestId("submit");

  await act(async () => {
    fireEvent.click(submit);
  });

  let errorDialog = screen.getByText(
    "Failed to create group. Group already exists.",
  );

  expect(errorDialog).toBeVisible();
  expect(callbackSpy).toHaveBeenCalled();
});
