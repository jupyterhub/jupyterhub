import React from "react";
import Enzyme, { mount } from "enzyme";
import AddUser from "./AddUser";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";
import { Provider, useDispatch } from "react-redux";
import { createStore } from "redux";
import { HashRouter } from "react-router-dom";

Enzyme.configure({ adapter: new Adapter() });

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useDispatch: jest.fn(),
}));

describe("AddUser Component: ", () => {
  var mockAsync = () =>
    jest.fn().mockImplementation(() => Promise.resolve({ key: "value" }));

  var addUserJsx = (callbackSpy) => (
    <Provider store={createStore(() => {}, {})}>
      <HashRouter>
        <AddUser
          addUsers={callbackSpy}
          failRegexEvent={callbackSpy}
          refreshUserData={callbackSpy}
          history={{ push: (a) => {} }}
        />
      </HashRouter>
    </Provider>
  );

  beforeEach(() => {
    useDispatch.mockImplementation((callback) => {
      return () => {};
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
