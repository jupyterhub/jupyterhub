import React from "react";
import Enzyme, { shallow } from "enzyme";
import Multiselect from "./Multiselect";
import Adapter from "@wojtekmaj/enzyme-adapter-react-17";

Enzyme.configure({ adapter: new Adapter() });

describe("Multiselect Component: ", () => {
  var multiselectJsx = () => (
    <Multiselect
      options={["foo", "bar", "wombat"]}
      s
      value={["wombat"]}
      onChange={() => {}}
    />
  );

  it("Renders with initial value selected", () => {
    let component = shallow(multiselectJsx()),
      selected = component.find(".item.selected").first();
    expect(selected.text()).toBe("wombat");
  });

  it("Deselects a value when div.item.selected is clicked", () => {
    let component = shallow(multiselectJsx()),
      selected = component.find(".item.selected").first();
    selected.simulate("click");
    expect(component.find(".item.selected").length).toBe(0);
  });

  it("Selects a an option when div.item.unselected is clicked", () => {
    let component = shallow(multiselectJsx()),
      unselected = component.find(".item.unselected").first();
    unselected.simulate("click");
    expect(component.find(".item.selected").length).toBe(2);
  });

  it("Triggers callback on any sort of change", () => {
    let callbackSpy = jest.fn(),
      component = shallow(
        <Multiselect
          options={["foo", "bar", "wombat"]}
          value={["wombat"]}
          onChange={callbackSpy}
        />
      ),
      selected = component.find(".item.selected").first();
    selected.simulate("click");
    expect(callbackSpy).toHaveBeenCalled();
  });
});
