import React, { Component, useState } from "react";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

const CreateGroup = (props) => {
  var [groupName, setGroupName] = useState("");

  var { createGroup, refreshGroupsData, history } = props;

  return (
    <>
      <div className="container">
        <div className="row">
          <div className="col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2">
            <div className="panel panel-default">
              <div className="panel-heading">
                <h4>Create Group</h4>
              </div>
              <div className="panel-body">
                <div className="input-group">
                  <input
                    className="group-name-input"
                    type="text"
                    value={groupName}
                    id="group-name"
                    placeholder="group name..."
                    onChange={(e) => {
                      setGroupName(e.target.value);
                    }}
                  ></input>
                </div>
              </div>
              <div className="panel-footer">
                <button id="return" className="btn btn-light">
                  <Link to="/">Back</Link>
                </button>
                <span> </span>
                <button
                  id="submit"
                  className="btn btn-primary"
                  onClick={() => {
                    let groupName = groupName;
                    createGroup(groupName)
                      .then(refreshGroupsData())
                      .then(history.push("/groups"))
                      .catch((err) => console.log(err));
                  }}
                >
                  Add Users
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

CreateGroup.propTypes = {
  createGroup: PropTypes.func,
  refreshGroupsData: PropTypes.func,
  failRegexEvent: PropTypes.func,
  history: PropTypes.shape({
    push: PropTypes.func,
  }),
};

export default CreateGroup;
