import React from "react";
import Enzyme, { shallow } from "enzyme";
import GroupEdit from "./GroupEdit.pre";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";

Enzyme.configure({ adapter: new Adapter() });

describe("GroupEdit Component: ", () => {
  var groupEditJsx = () => (
    <GroupEdit
      location={{
        state: {
          user_data: [{ name: "foo" }, { name: "bar" }],
          group_data: { users: ["foo"] },
          callback: () => {},
        },
      }}
      addToGroup={() => {}}
      removeFromGroup={() => {}}
      history={{ push: (a) => {} }}
    />
  );

  it("Can cleanly separate added and removed users", () => {
    let component = shallow(groupEditJsx()),
      submit = component.find("#submit");
    component.setState({ selected: ["bar"], changed: true });
    submit.simulate("click");
    expect(component.state("added")[0]).toBe("bar");
    expect(component.state("removed")[0]).toBe("foo");
  });
});
