import React from "react";
import Enzyme, { mount, shallow } from "enzyme";
import GroupEdit from "./GroupEdit";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";
import { Provider, useSelector } from "react-redux";
import { createStore } from "redux";
import { HashRouter } from "react-router-dom";

Enzyme.configure({ adapter: new Adapter() });

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useSelector: jest.fn(),
}));

describe("GroupEdit Component: ", () => {
  var mockAsync = () =>
    jest.fn().mockImplementation(() => Promise.resolve({ key: "value" }));

  var groupEditJsx = (callbackSpy) => (
    <Provider store={createStore(() => {}, {})}>
      <HashRouter>
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
          refreshGroupsData={callbackSpy}
        />
      </HashRouter>
    </Provider>
  );

  var mockAppState = () => ({
    user_data: JSON.parse(
      '[{"kind":"user","name":"foo","admin":true,"groups":[],"server":"/user/foo/","pending":null,"created":"2020-12-07T18:46:27.112695Z","last_activity":"2020-12-07T21:00:33.336354Z","servers":{"":{"name":"","last_activity":"2020-12-07T20:58:02.437408Z","started":"2020-12-07T20:58:01.508266Z","pending":null,"ready":true,"state":{"pid":28085},"url":"/user/foo/","user_options":{},"progress_url":"/hub/api/users/foo/server/progress"}}},{"kind":"user","name":"bar","admin":false,"groups":[],"server":null,"pending":null,"created":"2020-12-07T18:46:27.115528Z","last_activity":"2020-12-07T20:43:51.013613Z","servers":{}}]'
    ),
  });

  beforeEach(() => {
    useSelector.mockImplementation((callback) => {
      return callback(mockAppState());
    });
  });

  afterEach(() => {
    useSelector.mockClear();
  });

  it("Adds a newly selected user to group on submit", () => {
    let callbackSpy = mockAsync(),
      component = mount(groupEditJsx(callbackSpy)),
      unselected = component.find(".unselected"),
      submit = component.find("#submit");
    unselected.simulate("click");
    submit.simulate("click");
    expect(callbackSpy).toHaveBeenCalledWith(["bar"], "group");
  });

  it("Removes a user from group on submit", () => {
    let callbackSpy = mockAsync(),
      component = mount(groupEditJsx(callbackSpy)),
      selected = component.find(".selected"),
      submit = component.find("#submit");
    selected.simulate("click");
    submit.simulate("click");
    expect(callbackSpy).toHaveBeenCalledWith(["foo"], "group");
  });

  it("Calls deleteGroup on button click", () => {
    let callbackSpy = mockAsync(),
      component = mount(groupEditJsx(callbackSpy)),
      deleteGroup = component.find("#delete-group").first();
    deleteGroup.simulate("click");
    expect(callbackSpy).toHaveBeenNthCalledWith(1, "group");
    expect(callbackSpy).toHaveBeenNthCalledWith(2);
  });
});
