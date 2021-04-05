import React from "react";
import Enzyme, { shallow } from "enzyme";
import { Groups } from "./Groups.pre";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";

Enzyme.configure({ adapter: new Adapter() });

describe("Groups Component: ", () => {
  var groupsJsx = () => (
    <Groups
      user_data={JSON.parse(
        '[{"kind":"user","name":"foo","admin":true,"groups":[],"server":"/user/foo/","pending":null,"created":"2020-12-07T18:46:27.112695Z","last_activity":"2020-12-07T21:00:33.336354Z","servers":{"":{"name":"","last_activity":"2020-12-07T20:58:02.437408Z","started":"2020-12-07T20:58:01.508266Z","pending":null,"ready":true,"state":{"pid":28085},"url":"/user/foo/","user_options":{},"progress_url":"/hub/api/users/foo/server/progress"}}},{"kind":"user","name":"bar","admin":false,"groups":[],"server":null,"pending":null,"created":"2020-12-07T18:46:27.115528Z","last_activity":"2020-12-07T20:43:51.013613Z","servers":{}}]'
      )}
      groups_data={JSON.parse(
        '[{"kind":"group","name":"testgroup","users":[]}, {"kind":"group","name":"testgroup2","users":["foo", "bar"]}]'
      )}
    />
  );

  it("Renders groups_data prop into links", () => {
    let component = shallow(groupsJsx()),
      links = component.find(".group-edit-link");
    expect(links.length).toBe(2);
  });

  it("Renders nothing if required data is not available", () => {
    let component = shallow(<Groups />);
    expect(component.html()).toBe("<div></div>");
  });
});
