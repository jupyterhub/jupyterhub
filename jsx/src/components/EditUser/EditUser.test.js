import React from "react";
import Enzyme, { shallow } from "enzyme";
import EditUser from "./EditUser.pre";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";

Enzyme.configure({ adapter: new Adapter() });

describe("EditUser Component: ", () => {
  var mockAsync = () =>
    jest.fn().mockImplementation(() => Promise.resolve({ key: "value" }));
  var mockSync = () => jest.fn();

  var editUserJsx = (callbackSpy) => (
    <EditUser
      location={{ state: { username: "foo", has_admin: false } }}
      deleteUser={callbackSpy}
      editUser={callbackSpy}
      refreshUserData={mockSync()}
      history={{ push: (a) => {} }}
      failRegexEvent={callbackSpy}
    />
  );

  it("Updates the state whenever a key is pressed on the textarea", () => {
    let component = shallow(editUserJsx(mockAsync())),
      textarea = component.find("textarea");
    textarea.simulate("keydown", { target: { value: "test" } });
    expect(component.state("updated_username")).toBe("test");
  });

  it("Updates the state whenever the admin box changes", () => {
    let component = shallow(editUserJsx(mockAsync())),
      admin = component.find("#admin-check");
    admin.simulate("change", { target: { checked: true } });
    expect(component.state("admin")).toBe(true);
  });

  it("Delimits the input from the textarea", () => {
    let component = shallow(editUserJsx(mockAsync())),
      submit = component.find("#submit");
    component.setState({ updated_username: "%!@$#&" });
    submit.simulate("click");
    expect(component.state("updated_username")).toBe("");
  });

  it("Calls the delete user function when the button is pressed", () => {
    let callbackSpy = mockAsync(),
      component = shallow(editUserJsx(callbackSpy)),
      deleteUser = component.find("#delete-user");
    deleteUser.simulate("click");
    expect(callbackSpy).toHaveBeenCalled();
  });

  it("Submits the edits when the button is pressed", () => {
    let callbackSpy = mockAsync(),
      component = shallow(editUserJsx(callbackSpy)),
      submit = component.find("#submit"),
      textarea = component.find("textarea");
    textarea.simulate("keydown", { target: { value: "test" } });
    submit.simulate("click");
    expect(callbackSpy).toHaveBeenCalled();
  });
});
