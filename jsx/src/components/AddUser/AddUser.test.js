import React from "react";
import { act } from "react-dom/test-utils";
import Enzyme, { mount } from "enzyme";
import AddUser from "./AddUser";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";
import { Provider, useDispatch, useSelector } from "react-redux";
import { createStore } from "redux";
import { HashRouter } from "react-router-dom";
// eslint-disable-next-line
import regeneratorRuntime from 'regenerator-runtime'

Enzyme.configure({ adapter: new Adapter() });

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useDispatch: jest.fn(),
  useSelector: jest.fn(),
}));

var mockAsync = (statusCode) =>
  jest
    .fn()
    .mockImplementation(() =>
      Promise.resolve({ key: "value", status: statusCode ? statusCode : 200 })
    );

var mockAsyncRejection = () =>
  jest.fn().mockImplementation(() => Promise.reject());

var addUserJsx = (spy, spy2, spy3) => (
  <Provider store={createStore(() => {}, {})}>
    <HashRouter>
      <AddUser
        addUsers={spy}
        failRegexEvent={spy2 || spy}
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

test("Renders", () => {
  let component = mount(addUserJsx(mockAsync()));
  expect(component.find(".container").length).toBe(1);
});

test("Removes users when they fail Regex", () => {
  let callbackSpy = mockAsync(),
    component = mount(addUserJsx(callbackSpy)),
    textarea = component.find("textarea").first();
  textarea.simulate("blur", { target: { value: "foo\nbar\n!!*&*" } });
  let submit = component.find("#submit");
  submit.simulate("click");
  expect(callbackSpy).toHaveBeenCalledWith(["foo", "bar"], false);
});

test("Correctly submits admin", () => {
  let callbackSpy = mockAsync(),
    component = mount(addUserJsx(callbackSpy)),
    input = component.find("input").first();
  input.simulate("change", { target: { checked: true } });
  let submit = component.find("#submit");
  submit.simulate("click");
  expect(callbackSpy).toHaveBeenCalledWith([], true);
});

test("Shows a UI error dialogue when user creation fails", async () => {
  let callbackSpy = mockAsyncRejection(),
    component = mount(addUserJsx(callbackSpy));
  let submit = component.find("#submit");

  await act(async () => {
    submit.simulate("click");
  });

  component.update();
  let errorDialog = component.find("div.alert.alert-danger").first();

  expect(callbackSpy).toHaveBeenCalled();
  expect(errorDialog.text()).toContain("Failed to create user.");
});

test("Shows a more specific UI error dialogue when user creation returns an improper status code", async () => {
  let callbackSpy = mockAsync(409),
    component = mount(addUserJsx(callbackSpy));
  let submit = component.find("#submit");

  await act(async () => {
    submit.simulate("click");
  });

  component.update();
  let errorDialog = component.find("div.alert.alert-danger").first();

  expect(errorDialog.text()).toContain(
    "Failed to create user. User already exists."
  );
});
