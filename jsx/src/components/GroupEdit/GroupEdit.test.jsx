import React from "react";
import Enzyme, { mount } from "enzyme";
import GroupEdit from "./GroupEdit";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";
import { Provider, useSelector } from "react-redux";
import { createStore } from "redux";
import { HashRouter } from "react-router-dom";
import { act } from "react-dom/test-utils";
import regeneratorRuntime from "regenerator-runtime"; // eslint-disable-line

Enzyme.configure({ adapter: new Adapter() });

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useSelector: jest.fn(),
}));

describe("GroupEdit Component: ", () => {
  var mockAsync = () => jest.fn().mockImplementation(() => Promise.resolve());

  var okPacket = new Promise((resolve) => resolve(true));

  var groupEditJsx = (callbackSpy) => (
    <Provider store={createStore(() => {}, {})}>
      <HashRouter>
        <GroupEdit
          location={{
            state: {
              group_data: { users: ["foo"], name: "group" },
              callback: () => {},
            },
          }}
          addToGroup={callbackSpy}
          removeFromGroup={callbackSpy}
          deleteGroup={callbackSpy}
          history={{ push: () => callbackSpy }}
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
  });

  it("Adds user from input to user selectables on button click", async () => {
    let callbackSpy = mockAsync(),
      component = mount(groupEditJsx(callbackSpy)),
      input = component.find("#username-input"),
      validateUser = component.find("#validate-user"),
      submit = component.find("#submit");

    input.simulate("change", { target: { value: "bar" } });
    validateUser.simulate("click");
    await act(() => okPacket);
    submit.simulate("click");
    expect(callbackSpy).toHaveBeenNthCalledWith(1, ["bar"], "group");
  });

  it("Removes a user recently added from input from the selectables list", () => {
    let callbackSpy = mockAsync(),
      component = mount(groupEditJsx(callbackSpy)),
      unsubmittedUser = component.find(".item.selected").last();
    unsubmittedUser.simulate("click");
    expect(component.find(".item").length).toBe(1);
  });

  it("Grays out a user, already in the group, when unselected and calls deleteUser on submit", () => {
    let callbackSpy = mockAsync(),
      component = mount(groupEditJsx(callbackSpy)),
      groupUser = component.find(".item.selected").first();
    groupUser.simulate("click");
    expect(component.find(".item.unselected").length).toBe(1);
    expect(component.find(".item").length).toBe(1);
    // test deleteUser call
    let submit = component.find("#submit");
    submit.simulate("click");
    expect(callbackSpy).toHaveBeenNthCalledWith(1, ["foo"], "group");
  });

  it("Calls deleteGroup on button click", () => {
    let callbackSpy = mockAsync(),
      component = mount(groupEditJsx(callbackSpy)),
      deleteGroup = component.find("#delete-group").first();
    deleteGroup.simulate("click");
    expect(callbackSpy).toHaveBeenNthCalledWith(1, "group");
  });
});
