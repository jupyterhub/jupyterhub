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
      noChangeEvent={callbackSpy}
    />
  );

  it("Calls the delete user function when the button is pressed", () => {
    let callbackSpy = mockAsync(),
      component = shallow(editUserJsx(callbackSpy)),
      deleteUser = component.find("#delete-user");
    deleteUser.simulate("click");
    expect(callbackSpy).toHaveBeenCalled();
  });

  it("Submits the edits when the button is pressed", () => {
    let callbackSpy = mockSync(),
      component = shallow(editUserJsx(callbackSpy)),
      submit = component.find("#submit");
    submit.simulate("click");
    expect(callbackSpy).toHaveBeenCalled();
  });
});
