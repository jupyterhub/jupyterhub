import React, { useState, useEffect } from "react";
import "./table-select.css";
import PropTypes from "prop-types";

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

  const handleClick = () => {
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
    console.log(propkeys);
    console.log(propvalues);
    console.log(propobject);
  };

  const renderKeyRows = () => {
    if (propkeys) {
      return propkeys.map(function (o, i) {
        return (
          <tr key={"item-" + i}>
            <td>
              <input
                className="form-control"
                type="text"
                value={propkeys[i]}
                id={o}
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
          </tr>
        );
      });
    }
  };
  const renderValueRows = () => {
    if (propvalues) {
      return propvalues.map(function (o, i) {
        //console.log("ValRows" +i)
        //console.log("ValRows" +o)
        return (
          <tr key={"item-" + i}>
            <td>
              <input
                className="form-control"
                type="text"
                value={o}
                onChange={(e) => {
                  propvalues[i] = e.target.value;
                  props.setPropValues(propvalues);
                  setOwnValues(propvalues);
                  handleRefresh();
                }}
              />
            </td>
          </tr>
        );
      });
    }
  };
  const renderDelete = () => {
    if (propvalues) {
      return propvalues.map(function (o, i) {
        return (
          <tr key={"item-" + i}>
            <td>
              <button
                className="btn btn-default"
                onClick={() => {
                  propvalues.splice(i, 1);
                  propkeys.splice(i, 1);
                  var propobject = {};
                  propkeys.forEach(
                    (key, i) => (propobject[key] = propvalues[i]),
                  );
                  props.setProp(propobject);
                  props.setPropKeys(propkeys);
                  props.setPropValues(propvalues);
                  setOwnValues(propvalues);
                  setOwnKeys(propkeys);
                  handleRefresh();
                }}
              >
                Delete
              </button>
            </td>
          </tr>
        );
      });
    }
  };

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
            <td>{renderKeyRows()}</td>
            <td>{renderValueRows()}</td>
            <td>{renderDelete()}</td>
          </tr>
        </tbody>
      </table>
      <form>
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
            <button
              id="add-item"
              data-testid="add-item"
              className="btn btn-default"
              type="button"
              onClick={() => handleClick()}
            >
              Add Item
            </button>
          </td>
        </tr>
      </form>
      <hr />
    </div>
  );
};
DynamicTable.propTypes = {
  current_keys: PropTypes.array,
  current_values: PropTypes.array,
  setPropKeys: PropTypes.array,
  setPropValues: PropTypes.array,
  setProp: PropTypes.func,
};
export default DynamicTable;
