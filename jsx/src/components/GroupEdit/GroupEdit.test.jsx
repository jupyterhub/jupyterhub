import React, { act } from "react";
import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider, useSelector } from "react-redux";
import { createStore } from "redux";
import { HashRouter } from "react-router-dom";
// eslint-disable-next-line
import regeneratorRuntime from "regenerator-runtime";

import GroupEdit from "./GroupEdit";

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useSelector: jest.fn(),
}));

jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useLocation: jest.fn().mockImplementation(() => {
    return { state: { group_data: { users: ["foo"], name: "group" } } };
  }),
  useNavigate: jest.fn(),
}));

var mockAsync = (data) =>
  jest.fn().mockImplementation(() => Promise.resolve(data));

var mockAsyncRejection = () =>
  jest.fn().mockImplementation(() => Promise.reject());

var okPacket = new Promise((resolve) => resolve(true));

var groupEditJsx = (callbackSpy) => (
  <Provider store={createStore(() => {}, {})}>
    <HashRouter>
      <GroupEdit
        addToGroup={callbackSpy}
        removeFromGroup={callbackSpy}
        deleteGroup={callbackSpy}
        updateGroups={callbackSpy}
        validateUser={jest.fn().mockImplementation(() => okPacket)}
      />
    </HashRouter>
  </Provider>
);

var mockAppState = () => ({
  limit: 3,
});

beforeEach(() => {
  useSelector.mockImplementation((callback) => {
    return callback(mockAppState());
  });
});

afterEach(() => {
  useSelector.mockClear();
  jest.runAllTimers();
});

test("Renders", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(groupEditJsx(callbackSpy));
  });

  expect(screen.getByTestId("container")).toBeVisible();
});

test("Adds user from input to user selectables on button click", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(groupEditJsx(callbackSpy));
  });

  let input = screen.getByTestId("username-input");
  let validateUser = screen.getByTestId("validate-user");
  let submit = screen.getByTestId("submit");
  const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
  await user.type(input, "bar");
  await user.click(validateUser);
  await act(async () => {
    await jest.runAllTimers();
  });

  await act(async () => {
    await fireEvent.click(submit);
  });

  expect(callbackSpy).toHaveBeenNthCalledWith(1, ["bar"], "group");
});

test("Removes a user recently added from input from the selectables list", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(groupEditJsx(callbackSpy));
  });

  let selectedUser = screen.getByText("foo");
  await await fireEvent.click(selectedUser);

  let unselectedUser = screen.getByText("foo");

  expect(unselectedUser.className).toBe("item unselected");
});

test("Grays out a user, already in the group, when unselected and calls deleteUser on submit", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(groupEditJsx(callbackSpy));
  });

  let submit = screen.getByTestId("submit");

  let groupUser = screen.getByText("foo");
  await fireEvent.click(groupUser);

  let unselectedUser = screen.getByText("foo");
  expect(unselectedUser.className).toBe("item unselected");

  // test deleteUser call
  await act(async () => {
    await fireEvent.click(submit);
  });

  expect(callbackSpy).toHaveBeenNthCalledWith(1, ["foo"], "group");
});

test("Calls deleteGroup on button click", async () => {
  let callbackSpy = mockAsync();

  await act(async () => {
    render(groupEditJsx(callbackSpy));
  });

  let deleteGroup = screen.getByTestId("delete-group");

  await act(async () => {
    await fireEvent.click(deleteGroup);
  });

  expect(callbackSpy).toHaveBeenNthCalledWith(1, "group");
});

test("Shows a UI error dialogue when group edit fails", async () => {
  let callbackSpy = mockAsyncRejection();

  await act(async () => {
    render(groupEditJsx(callbackSpy));
  });

  let groupUser = screen.getByText("foo");
  await fireEvent.click(groupUser);

  let submit = screen.getByTestId("submit");

  await act(async () => {
    await fireEvent.click(submit);
  });

  let errorDialog = screen.getByText("Failed to edit group.");

  expect(errorDialog).toBeVisible();
  expect(callbackSpy).toHaveBeenCalled();
});

test("Shows a UI error dialogue when group edit returns an improper status code", async () => {
  let callbackSpy = mockAsync({ status: 403 });

  await act(async () => {
    render(groupEditJsx(callbackSpy));
  });

  let groupUser = screen.getByText("foo");
  await fireEvent.click(groupUser);

  let submit = screen.getByTestId("submit");

  await act(async () => {
    await fireEvent.click(submit);
  });

  let errorDialog = screen.getByText("Failed to edit group.");

  expect(errorDialog).toBeVisible();
  expect(callbackSpy).toHaveBeenCalled();
});

test("Shows a UI error dialogue when group delete fails", async () => {
  let callbackSpy = mockAsyncRejection();

  await act(async () => {
    render(groupEditJsx(callbackSpy));
  });

  let deleteGroup = screen.getByTestId("delete-group");

  await act(async () => {
    await fireEvent.click(deleteGroup);
  });

  let errorDialog = screen.getByText("Failed to delete group.");

  expect(errorDialog).toBeVisible();
  expect(callbackSpy).toHaveBeenCalled();
});

test("Shows a UI error dialogue when group delete returns an improper status code", async () => {
  let callbackSpy = mockAsync({ status: 403 });

  await act(async () => {
    render(groupEditJsx(callbackSpy));
  });

  let deleteGroup = screen.getByTestId("delete-group");

  await act(async () => {
    await fireEvent.click(deleteGroup);
  });

  let errorDialog = screen.getByText("Failed to delete group.");

  expect(errorDialog).toBeVisible();
  expect(callbackSpy).toHaveBeenCalled();
});
