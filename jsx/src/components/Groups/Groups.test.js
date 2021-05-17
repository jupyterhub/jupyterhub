import React from "react";
import Enzyme, { mount } from "enzyme";
import Groups from "./Groups";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";
import { Provider, useDispatch, useSelector } from "react-redux";
import { createStore } from "redux";
import { HashRouter } from "react-router-dom";

Enzyme.configure({ adapter: new Adapter() });

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useSelector: jest.fn(),
  useDispatch: jest.fn(),
}));

describe("Groups Component: ", () => {
  var mockAsync = () =>
    jest.fn().mockImplementation(() => Promise.resolve({ key: "value" }));

  var groupsJsx = (callbackSpy) => (
    <Provider store={createStore(() => {}, {})}>
      <HashRouter>
        <Groups location={{ search: "0" }} updateGroups={callbackSpy} />
      </HashRouter>
    </Provider>
  );

  var mockAppState = () => ({
    user_data: JSON.parse(
      '[{"kind":"user","name":"foo","admin":true,"groups":[],"server":"/user/foo/","pending":null,"created":"2020-12-07T18:46:27.112695Z","last_activity":"2020-12-07T21:00:33.336354Z","servers":{"":{"name":"","last_activity":"2020-12-07T20:58:02.437408Z","started":"2020-12-07T20:58:01.508266Z","pending":null,"ready":true,"state":{"pid":28085},"url":"/user/foo/","user_options":{},"progress_url":"/hub/api/users/foo/server/progress"}}},{"kind":"user","name":"bar","admin":false,"groups":[],"server":null,"pending":null,"created":"2020-12-07T18:46:27.115528Z","last_activity":"2020-12-07T20:43:51.013613Z","servers":{}}]'
    ),
    groups_data: JSON.parse(
      '[{"kind":"group","name":"testgroup","users":[]}, {"kind":"group","name":"testgroup2","users":["foo", "bar"]}]'
    ),
  });

  beforeEach(() => {
    useSelector.mockImplementation((callback) => {
      return callback(mockAppState());
    });
    useDispatch.mockImplementation(() => {
      return () => {};
    });
  });

  afterEach(() => {
    useSelector.mockClear();
  });

  it("Renders groups_data prop into links", () => {
    let callbackSpy = mockAsync(),
      component = mount(groupsJsx(callbackSpy)),
      links = component.find("li");
    expect(links.length).toBe(2);
  });

  it("Renders nothing if required data is not available", () => {
    useSelector.mockImplementation((callback) => {
      return callback({});
    });
    let component = mount(groupsJsx());
    expect(component.html()).toBe("<div></div>");
  });
});
