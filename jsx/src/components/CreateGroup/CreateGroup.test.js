import React from "react";
import Enzyme, { mount, shallow } from "enzyme";
import CreateGroup from "./CreateGroup.pre";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";

Enzyme.configure({ adapter: new Adapter() });

describe("CreateGroup Component: ", () => {
  var mockAsync = () =>
    jest.fn().mockImplementation(() => Promise.resolve({ key: "value" }));

  var createGroupJsx = (callbackSpy) => 
    <CreateGroup
      createGroup={callbackSpy}
      refreshGroupsData={callbackSpy}
      history={{push: () => {}}}
    />

  it("Renders", () => {
    let component = shallow(createGroupJsx())
    expect(component.find(".container").length).toBe(1)
  })

  it("Calls createGroup and refreshGroupsData on submit", () => {
    let callbackSpy = mockAsync(),
      component = shallow(createGroupJsx(callbackSpy)),
      input = component.find("input").first(),
      submit = component.find("#submit").first()
    input.simulate("change", { target: { value: "" } })
    submit.simulate("click")
    expect(callbackSpy).toHaveBeenNthCalledWith(1, "")
    expect(callbackSpy).toHaveBeenNthCalledWith(2)
  })
})