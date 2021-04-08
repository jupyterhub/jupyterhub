import React from "react";
import Enzyme, { mount, shallow } from "enzyme";
import GroupEdit from "./GroupEdit.pre";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";
import { HashRouter } from "react-router-dom";

Enzyme.configure({ adapter: new Adapter() });

describe("GroupEdit Component: ", () => {
  var mockAsync = () =>
    jest.fn().mockImplementation(() => Promise.resolve({ key: "value" }));

  var groupEditJsx = (callbackSpy) => (
    <GroupEdit
      location={{
        state: {
          user_data: [{ name: "foo" }, { name: "bar" }],
          group_data: { users: ["foo"], name: "group" },
          callback: () => {},
        },
      }}
      addToGroup={callbackSpy}
      removeFromGroup={callbackSpy}
      deleteGroup={callbackSpy}
      history={{ push: (a) => callbackSpy }}
      refreshGroupsData={() => {}}
    />
  );

  var deepGroupEditJsx = (callbackSpy) => (
    <HashRouter>{groupEditJsx(callbackSpy)}</HashRouter>
  );

  it("Adds a newly selected user to group on submit", () => {
    let callbackSpy = mockAsync(),
      component = mount(deepGroupEditJsx(callbackSpy)),
      unselected = component.find(".unselected"),
      submit = component.find("#submit");
    unselected.simulate("click");
    submit.simulate("click");
    expect(callbackSpy).toHaveBeenCalledWith(["bar"], "group");
  });

  it("Removes a user from group on submit", () => {
    let callbackSpy = mockAsync(),
      component = mount(deepGroupEditJsx(callbackSpy)),
      selected = component.find(".selected"),
      submit = component.find("#submit");
    selected.simulate("click");
    submit.simulate("click");
    expect(callbackSpy).toHaveBeenCalledWith(["foo"], "group");
  });

  it("Calls deleteGroup on button click", () => {
    let callbackSpy = mockAsync(),
      component = shallow(groupEditJsx(callbackSpy)),
      deleteGroup = component.find("#delete-group").first();
    deleteGroup.simulate("click");
    expect(callbackSpy).toHaveBeenCalled();
  });
});
