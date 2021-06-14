import React from "react";
import Enzyme, { mount } from "enzyme";
import AddUser from "./AddUser";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";
import { Provider, useDispatch, useSelector } from "react-redux";
import { createStore } from "redux";
import { HashRouter } from "react-router-dom";

Enzyme.configure({ adapter: new Adapter() });

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useDispatch: jest.fn(),
  useSelector: jest.fn(),
}));

describe("AddUser Component: ", () => {
  var mockAsync = () =>
    jest
      .fn()
      .mockImplementation(() => Promise.resolve({ key: "value", status: 200 }));

  var addUserJsx = (callbackSpy) => (
    <Provider store={createStore(() => {}, {})}>
      <HashRouter>
        <AddUser
          addUsers={callbackSpy}
          failRegexEvent={callbackSpy}
          updateUsers={callbackSpy}
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

  it("Renders", () => {
    let component = mount(addUserJsx(mockAsync()));
    expect(component.find(".container").length).toBe(1);
  });

  it("Removes users when they fail Regex", () => {
    let callbackSpy = mockAsync(),
      component = mount(addUserJsx(callbackSpy)),
      textarea = component.find("textarea").first();
    textarea.simulate("blur", { target: { value: "foo\nbar\n!!*&*" } });
    let submit = component.find("#submit");
    submit.simulate("click");
    expect(callbackSpy).toHaveBeenCalledWith(["foo", "bar"], false);
  });

  it("Correctly submits admin", () => {
    let callbackSpy = mockAsync(),
      component = mount(addUserJsx(callbackSpy)),
      input = component.find("input").first();
    input.simulate("change", { target: { checked: true } });
    let submit = component.find("#submit");
    submit.simulate("click");
    expect(callbackSpy).toHaveBeenCalledWith([], true);
  });
});
