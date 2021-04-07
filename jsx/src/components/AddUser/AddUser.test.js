import React from "react";
import Enzyme, { shallow } from "enzyme";
import AddUser from "./AddUser.pre";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";

Enzyme.configure({ adapter: new Adapter() });

describe("AddUser Component: ", () => {
  var mockAsync = () =>
    jest.fn().mockImplementation(() => Promise.resolve({ key: "value" }));

  var addUserJsx = (callbackSpy) => (
    <AddUser
      addUsers={callbackSpy}
      failRegexEvent={callbackSpy}
      refreshUserData={callbackSpy}
      history={{ push: (a) => {} }}
    />
  );

  it("Renders", () => {
    let component = shallow(addUserJsx(mockAsync()));
    expect(component.find(".container").length).toBe(1);
  });

  it("Removes users when they fail Regex", () => {
    let callbackSpy = mockAsync(),
      component = shallow(addUserJsx(callbackSpy)),
      textarea = component.find("textarea").first();
    textarea.simulate("blur", { target: { value: "foo\nbar\n!!*&*" } });
    let submit = component.find("#submit");
    submit.simulate("click");
    expect(callbackSpy).toHaveBeenCalledWith(["foo", "bar"], false);
  });

  it("Correctly submits admin", () => {
    let callbackSpy = mockAsync(),
      component = shallow(addUserJsx(callbackSpy)),
      input = component.find("input").first();
    input.simulate("change", { target: { checked: true } });
    let submit = component.find("#submit");
    submit.simulate("click");
    expect(callbackSpy).toHaveBeenCalledWith([], true);
  });
});
