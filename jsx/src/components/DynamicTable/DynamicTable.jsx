import React, { useState } from "react";
import "./table-select.css";
import PropTypes from "prop-types";
import { Button } from "react-bootstrap";

const DynamicTable = (props) => {
  var [message, setMessage] = useState(""),
    [message2, setMessage2] = useState("");
  var { current_propobject } = props;

  var propobject = current_propobject;

  if (current_propobject) {
    var [propkeys, setOwnKeys] = useState(Object.keys(current_propobject));
    var [propvalues, setOwnValues] = useState(
      Object.values(current_propobject),
    );
  }

  var updateMessageKey = (event) => {
    setMessage(event.target.value);
  };
  var updateMessageValue = (event) => {
    setMessage2(event.target.value);
  };
  const handleRefresh = () => {
    var propobject = {};
    propkeys.forEach((key, i) => (propobject[key] = propvalues[i]));
    props.setProp(propobject);
    props.setPropKeys(propkeys);
    props.setPropValues(propvalues);
    setMessage("");
    setMessage2("");
  };

  const handleAddItem = () => {
    if (message != "") {
      if (message2 != "") {
        propkeys.push(message);
        propvalues.push(message2);
      } else {
        console.log("Value not valid");
      }
    } else {
      console.log("Value not valid");
    }
    var propobject = {};
    propkeys.forEach((key, i) => (propobject[key] = propvalues[i]));
    props.setProp(propobject);
    props.setPropKeys(propkeys);
    setOwnKeys(propkeys);
    props.setPropValues(propvalues);
    setOwnValues(propvalues);
    setMessage("");
    setMessage2("");
  };

  const KeyValueRow = (i) => {
    // one table row for a key-value pair
    const key = propkeys[i];
    const value = propvalues[i];
    return (
      <tr key={"item-" + i}>
        <td>
          <input
            className="form-control"
            type="text"
            value={propkeys[i]}
            id={key}
            onChange={(e) => {
              if (e.target.value != "") {
                propkeys[i] = e.target.value;
              } else {
                propvalues.splice(i, 1);
                propkeys.splice(i, 1);
              }
              setOwnKeys(propkeys);
              props.setPropKeys(propkeys);
              props.setProp(propobject);
              handleRefresh();
            }}
          />
        </td>
        <td>
          <input
            className="form-control"
            type="text"
            value={value}
            onChange={(e) => {
              propvalues[i] = e.target.value;
              props.setPropValues(propvalues);
              setOwnValues(propvalues);
              handleRefresh();
            }}
          />
        </td>
        <td>
          <Button
            variant="danger"
            onClick={() => {
              propvalues.splice(i, 1);
              propkeys.splice(i, 1);
              var propobject = {};
              propkeys.forEach((key, i) => (propobject[key] = propvalues[i]));
              props.setProp(propobject);
              props.setPropKeys(propkeys);
              props.setPropValues(propvalues);
              setOwnValues(propvalues);
              setOwnKeys(propkeys);
              handleRefresh();
            }}
          >
            Delete
          </Button>
        </td>
      </tr>
    );
  };

  const renderKeyValueRows = () => {
    if (!propkeys) return null;
    return propkeys.map((key, i) => KeyValueRow(i));
  };

  return (
    <div>
      <table className="properties-table">
        <thead>
          <tr>
            <th>Key</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          {renderKeyValueRows()}
          <tr>
            <td>
              <input
                className="form-control"
                type="text"
                value={message}
                onChange={(e) => updateMessageKey(e)}
              />
            </td>
            <td>
              <input
                className="form-control"
                type="text"
                value={message2}
                onChange={(e) => updateMessageValue(e)}
              />
            </td>
            <td>
              <Button
                id="add-item"
                data-testid="add-item"
                className="text-nowrap"
                onClick={() => handleAddItem()}
              >
                Add Item
              </Button>
            </td>
          </tr>
        </tbody>
      </table>
      <hr />
    </div>
  );
};
DynamicTable.propTypes = {
  current_keys: PropTypes.array,
  current_values: PropTypes.array,
  current_propobject: PropTypes.object,
  setPropKeys: PropTypes.func,
  setPropValues: PropTypes.func,
  setProp: PropTypes.func,
};
export default DynamicTable;
