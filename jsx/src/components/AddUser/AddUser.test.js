import React from "react";
import Enzyme, { shallow } from "enzyme";
import { AddUser } from "./AddUser.pre";
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

  it("Updates state.users on textbox blur", () => {
    let component = shallow(addUserJsx(mockAsync())),
      textarea = component.find("textarea");
    textarea.simulate("blur", { target: { value: "foo" } });
    expect(JSON.stringify(component.state("users"))).toBe('["foo"]');
  });

  it("Can separate newline spaced names into an array", () => {
    let component = shallow(addUserJsx(mockAsync())),
      textarea = component.find("textarea");
    textarea.simulate("blur", { target: { value: "foo\nbar\nsoforth" } });
    expect(JSON.stringify(component.state("users"))).toBe(
      '["foo","bar","soforth"]'
    );
  });

  it("Deliminates names with special / less than 3 characters", () => {
    let component = shallow(addUserJsx(mockAsync())),
      textarea = component.find("textarea"),
      submit = component.find("#submit");
    textarea.simulate("blur", {
      target: { value: "foo\nbar\nb%%%\n$andy\nhalfdecent" },
    });
    submit.simulate("click");
    expect(JSON.stringify(component.state("users"))).toBe(
      '["foo","bar","halfdecent"]'
    );
  });

  it("Recognizes admin user selection", () => {
    let component = shallow(addUserJsx(mockAsync())),
      admin = component.find("#admin-check");
    admin.simulate("change", { target: { checked: true } });
    expect(component.state("admin")).toBe(true);
  });
});
