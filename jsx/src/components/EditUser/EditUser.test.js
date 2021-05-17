import React from "react";
import Enzyme, { mount } from "enzyme";
import EditUser from "./EditUser";
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

describe("EditUser Component: ", () => {
  var mockAsync = () =>
    jest
      .fn()
      .mockImplementation(() => Promise.resolve({ key: "value", status: 200 }));
  var mockSync = () => jest.fn();

  var editUserJsx = (callbackSpy, empty) => (
    <Provider store={createStore(() => {}, {})}>
      <HashRouter>
        <EditUser
          location={
            empty ? {} : { state: { username: "foo", has_admin: false } }
          }
          deleteUser={callbackSpy}
          editUser={callbackSpy}
          updateUsers={callbackSpy}
          history={{ push: () => {} }}
          failRegexEvent={callbackSpy}
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

  it("Calls the delete user function when the button is pressed", () => {
    let callbackSpy = mockAsync(),
      component = mount(editUserJsx(callbackSpy)),
      deleteUser = component.find("#delete-user");
    deleteUser.simulate("click");
    expect(callbackSpy).toHaveBeenCalled();
  });

  it("Submits the edits when the button is pressed", () => {
    let callbackSpy = mockSync(),
      component = mount(editUserJsx(callbackSpy)),
      submit = component.find("#submit");
    submit.simulate("click");
    expect(callbackSpy).toHaveBeenCalled();
  });

  it("Doesn't render when no data is provided", () => {
    let callbackSpy = mockSync(),
      component = mount(editUserJsx(callbackSpy, true));
    expect(component.find(".container").length).toBe(0);
  });
});
