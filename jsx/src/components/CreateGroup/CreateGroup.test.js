import React from "react";
import Enzyme, { mount } from "enzyme";
import CreateGroup from "./CreateGroup";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";
import { Provider, useDispatch, useSelector } from "react-redux";
import { createStore } from "redux";
import { HashRouter } from "react-router-dom";
import regeneratorRuntime from "regenerator-runtime"; // eslint-disable-line

Enzyme.configure({ adapter: new Adapter() });

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useDispatch: jest.fn(),
  useSelector: jest.fn(),
}));

describe("CreateGroup Component: ", () => {
  var mockAsync = (result) =>
    jest.fn().mockImplementation(() => Promise.resolve(result));

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

  it("Renders", () => {
    let component = mount(createGroupJsx());
    expect(component.find(".container").length).toBe(1);
  });

  it("Calls createGroup on submit", () => {
    let callbackSpy = mockAsync({ status: 200 }),
      component = mount(createGroupJsx(callbackSpy)),
      input = component.find("input").first(),
      submit = component.find("#submit").first();
    input.simulate("change", { target: { value: "" } });
    submit.simulate("click");
    expect(callbackSpy).toHaveBeenNthCalledWith(1, "");
    expect(component.find(".alert.alert-danger").length).toBe(0);
  });
});
