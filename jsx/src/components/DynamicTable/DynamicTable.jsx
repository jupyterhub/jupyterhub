import React, { useState } from "react";
import "./table-select.css";

export default class DynamicTable extends React.Component {
  constructor(props) {
    super(props);
    this.current_propobject = props.current_propobject;
    this.setProp = props.setProp;
    this.setPropKeys = props.setPropKeys;
    this.setPropValues = props.setPropValues;

    let current_keys = [];
    let current_values = [];

    for (var property in this.current_propobject) {
      current_keys.push(property);
      current_values.push(this.current_propobject[property]);
    }
    //current_keys = this.current_propobject.propkeys
    //current_values = this.current_propobject.propvalues

    this.state = {
      message: "",
      message2: "",
      propkeys: current_keys,
      propvalues: current_values,
      propobject: "",
    };
  }

  updateMessageKey(event) {
    this.setState({
      message: event.target.value,
    });
  }

  updateMessageValue(event) {
    this.setState({
      message2: event.target.value,
    });
  }
  handleRefresh(i) {
    var propkeys = this.state.propkeys;
    var propvalues = this.state.propvalues;
    var propobject = {};
    propkeys.forEach((key, i) => (propobject[key] = propvalues[i]));

    console.log(propobject);
    this.setProp(propobject);
    this.setPropKeys(propkeys);
    this.setPropValues(propvalues);

    this.setState({
      propkeys: propkeys,
      propvalues: propvalues,
      message: "",
      message2: "",
      propobject: propobject,
    });
  }
  handleClick() {
    var propkeys = this.state.propkeys;
    var propvalues = this.state.propvalues;
    if (this.state.message != "") {
      if (this.state.message2 != "") {
        propkeys.push(this.state.message);
        propvalues.push(this.state.message2);
      } else {
        console.log("Value not valid");
      }
    } else {
      console.log("Value not valid");
    }

    var propobject = {};
    propkeys.forEach((key, i) => (propobject[key] = propvalues[i]));
    console.log(propobject);
    this.setProp(propobject);
    this.setPropKeys(propkeys);
    this.setPropValues(propvalues);
    this.setState({
      propkeys: propkeys,
      propvalues: propvalues,
      message: "",
      message2: "",
      propobject: propobject,
    });
  }

  handleValueChanged(i, event) {
    var propvalues = this.state.propvalues;
    var propkeys = this.state.propkeys;
    propvalues[i] = event.target.value;

    this.handleRefresh();
    this.setPropKeys(propkeys);
    this.setPropValues(propvalues);
    this.setState({
      propvalues: propvalues,
    });
  }
  handleKeyChanged(i, event) {
    var propkeys = this.state.propkeys;

    if (event.target.value != "") {
      propkeys[i] = event.target.value;
    }
    console.log(event.target.value);

    if (event.target.value == "") {
      this.handleItemDeleted(i);
    }
    this.handleRefresh(i);
    this.setPropKeys(propkeys);
    this.setState({
      propkeys: propkeys,
    });
  }

  handleItemDeleted(i) {
    var propvalues = this.state.propvalues;
    var propkeys = this.state.propkeys;

    propvalues.splice(i, 1);
    propkeys.splice(i, 1);
    this.setPropKeys(propkeys);
    this.setPropValues(propvalues);
    this.handleRefresh(i);
    this.setState({
      propvalues: propvalues,
      propkeys: propkeys,
    });
  }

  renderKeyRows() {
    var context = this;

    return this.state.propkeys.map(function (o, i) {
      return (
        <tr key={"item-" + i}>
          <td>
            <input
              className="form-control"
              type="text"
              value={o}
              id={o + i}
              onChange={context.handleKeyChanged.bind(context, i)}
            />
          </td>
        </tr>
      );
    });
  }
  renderValueRows() {
    var context = this;

    return this.state.propvalues.map(function (o, i) {
      return (
        <tr key={"item-" + i}>
          <td>
            <input
              className="form-control"
              type="text"
              value={o}
              onChange={context.handleValueChanged.bind(context, i)}
            />
          </td>
        </tr>
      );
    });
  }
  renderDelete() {
    var context = this;

    return this.state.propvalues.map(function (o, i) {
      return (
        <tr key={"item-" + i}>
          <td>
            <button
              className="btn btn-default"
              onClick={context.handleItemDeleted.bind(context, i)}
            >
              Delete
            </button>
          </td>
        </tr>
      );
    });
  }

  render() {
    return (
      <div>
        <table className="">
          <thead>
            <tr>
              <th>Key</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{this.renderKeyRows()}</td>
              <td>{this.renderValueRows()}</td>
              <td>{this.renderDelete()}</td>
            </tr>
          </tbody>
        </table>
        <form>
          <tr>
            <td>
              <input
                className="form-control"
                type="text"
                value={this.state.message}
                onChange={this.updateMessageKey.bind(this)}
              />
            </td>
            <td>
              <input
                className="form-control"
                type="text"
                value={this.state.message2}
                onChange={this.updateMessageValue.bind(this)}
              />
            </td>
            <td>
              <button
                id="add-item"
                data-testid="add-item"
                className="btn btn-default"
                type="button"
                onClick={this.handleClick.bind(this)}
              >
                Add Item
              </button>
            </td>
          </tr>
        </form>
        <hr />
      </div>
    );
  }
}
