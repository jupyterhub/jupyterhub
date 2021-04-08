import React, { useState } from "react";
import { useDispatch } from "react-redux";
import { compose, withProps } from "recompose";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";
import { jhapiRequest } from "../../util/jhapiUtil";

const CreateGroup = (props) => {
  var [groupName, setGroupName] = useState("");

  var dispatch = useDispatch();

  var dispatchGroupsData = (data) => {
    dispatch({
      type: "GROUPS_DATA",
      value: data,
    });
  };

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
                    id="group-name"
                    value={groupName}
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
                    createGroup(groupName)
                      .then(
                        refreshGroupsData()
                          .then((data) => dispatchGroupsData(data))
                          .catch((err) => console.log(err))
                      )
                      .then(history.push("/groups"))
                      .catch((err) => console.log(err));
                  }}
                >
                  Create
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

const withGroupsAPI = withProps((props) => ({
  createGroup: (groupName) => jhapiRequest("/groups/" + groupName, "POST"),
  failRegexEvent: () =>
    alert(
      "Removed " +
        JSON.stringify(removed_users) +
        " for either containing special characters or being too short."
    ),
  refreshGroupsData: () =>
    jhapiRequest("/groups", "GET").then((data) => data.json()),
}));

export default compose(withGroupsAPI)(CreateGroup);
