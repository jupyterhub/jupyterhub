import React from "react";
import Enzyme, { mount } from "enzyme";
import ServerDashboard from "./ServerDashboard";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";
import { HashRouter, Switch } from "react-router-dom";
import { Provider, useSelector } from "react-redux";
import { createStore } from "redux";

Enzyme.configure({ adapter: new Adapter() });

jest.mock("react-redux", () => ({
  ...jest.requireActual("react-redux"),
  useSelector: jest.fn(),
}));

describe("ServerDashboard Component: ", () => {
  var serverDashboardJsx = (callbackSpy) => (
    <Provider store={createStore(() => {}, {})}>
      <HashRouter>
        <Switch>
          <ServerDashboard
            updateUsers={callbackSpy}
            shutdownHub={callbackSpy}
            startServer={callbackSpy}
            stopServer={callbackSpy}
            startAll={callbackSpy}
            stopAll={callbackSpy}
          />
        </Switch>
      </HashRouter>
    </Provider>
  );

  var mockAsync = () =>
    jest
      .fn()
      .mockImplementation(() =>
        Promise.resolve({ json: () => Promise.resolve({ k: "v" }) })
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

  it("Renders users from props.user_data into table", () => {
    let component = mount(serverDashboardJsx(mockAsync())),
      userRows = component.find(".user-row");
    expect(userRows.length).toBe(2);
  });

  it("Renders correctly the status of a single-user server", () => {
    let component = mount(serverDashboardJsx(mockAsync())),
      userRows = component.find(".user-row");
    // Renders .stop-button when server is started
    // Should be 1 since user foo is started
    expect(userRows.at(0).find(".stop-button").length).toBe(1);
    // Renders .start-button when server is stopped
    // Should be 1 since user bar is stopped
    expect(userRows.at(1).find(".start-button").length).toBe(1);
  });

  it("Invokes the startServer event on button click", () => {
    let callbackSpy = mockAsync(),
      component = mount(serverDashboardJsx(callbackSpy)),
      startBtn = component.find(".start-button");
    startBtn.simulate("click");
    expect(callbackSpy).toHaveBeenCalled();
  });

  it("Invokes the stopServer event on button click", () => {
    let callbackSpy = mockAsync(),
      component = mount(serverDashboardJsx(callbackSpy)),
      stopBtn = component.find(".stop-button");
    stopBtn.simulate("click");
    expect(callbackSpy).toHaveBeenCalled();
  });

  it("Invokes the shutdownHub event on button click", () => {
    let callbackSpy = mockAsync(),
      component = mount(serverDashboardJsx(callbackSpy)),
      shutdownBtn = component.find("#shutdown-button").first();
    shutdownBtn.simulate("click");
    expect(callbackSpy).toHaveBeenCalled();
  });

  it("Sorts according to username", () => {
    let component = mount(serverDashboardJsx(mockAsync())).find(
        "ServerDashboard"
      ),
      handler = component.find("SortHandler").first();
    handler.simulate("click");
    let first = component.find(".user-row").first();
    expect(first.html().includes("bar")).toBe(true);
    handler.simulate("click");
    first = component.find(".user-row").first();
    expect(first.html().includes("foo")).toBe(true);
  });

  it("Sorts according to admin", () => {
    let component = mount(serverDashboardJsx(mockAsync())).find(
        "ServerDashboard"
      ),
      handler = component.find("SortHandler").at(1);
    handler.simulate("click");
    let first = component.find(".user-row").first();
    expect(first.html().includes("admin")).toBe(true);
    handler.simulate("click");
    first = component.find(".user-row").first();
    expect(first.html().includes("admin")).toBe(false);
  });

  it("Sorts according to last activity", () => {
    let component = mount(serverDashboardJsx(mockAsync())).find(
        "ServerDashboard"
      ),
      handler = component.find("SortHandler").at(2);
    handler.simulate("click");
    let first = component.find(".user-row").first();
    // foo used most recently
    expect(first.html().includes("foo")).toBe(true);
    handler.simulate("click");
    first = component.find(".user-row").first();
    // invert sort - bar used least recently
    expect(first.html().includes("bar")).toBe(true);
  });

  it("Sorts according to server status (running/not running)", () => {
    let component = mount(serverDashboardJsx(mockAsync())).find(
        "ServerDashboard"
      ),
      handler = component.find("SortHandler").at(3);
    handler.simulate("click");
    let first = component.find(".user-row").first();
    // foo running
    expect(first.html().includes("foo")).toBe(true);
    handler.simulate("click");
    first = component.find(".user-row").first();
    // invert sort - bar not running
    expect(first.html().includes("bar")).toBe(true);
  });

  it("Renders nothing if required data is not available", () => {
    useSelector.mockImplementation((callback) => {
      return callback({});
    });
    let component = mount(serverDashboardJsx(jest.fn()));
    expect(component.html()).toBe("<div></div>");
  });
});
