import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

const CreateGroup = (props) => {
  var [groupName, setGroupName] = useState(""),
    [errorAlert, setErrorAlert] = useState(null),
    limit = useSelector((state) => state.limit);

  var dispatch = useDispatch();

  var dispatchPageUpdate = (data, page) => {
    dispatch({
      type: "GROUPS_PAGE",
      value: {
        data: data,
        page: page,
      },
    });
  };

  var { createGroup, updateGroups, history } = props;

  return (
    <>
      <div className="container" data-testid="container">
        {errorAlert != null ? (
          <div className="row">
            <div className="col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2">
              <div className="alert alert-danger">
                {errorAlert}
                <button
                  type="button"
                  className="close"
                  onClick={() => setErrorAlert(null)}
                >
                  <span>&times;</span>
                </button>
              </div>
            </div>
          </div>
        ) : (
          <></>
        )}
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
                    data-testid="group-input"
                    type="text"
                    id="group-name"
                    value={groupName}
                    placeholder="group name..."
                    onChange={(e) => {
                      setGroupName(e.target.value.trim());
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
                  data-testid="submit"
                  className="btn btn-primary"
                  onClick={() => {
                    createGroup(groupName)
                      .then((data) => {
                        return data.status < 300
                          ? updateGroups(0, limit)
                              .then((data) => dispatchPageUpdate(data, 0))
                              .then(() => history.push("/groups"))
                              .catch(() =>
                                setErrorAlert(`Could not update groups list.`),
                              )
                          : setErrorAlert(
                              `Failed to create group. ${
                                data.status == 409
                                  ? "Group already exists."
                                  : ""
                              }`,
                            );
                      })
                      .catch(() => setErrorAlert(`Failed to create group.`));
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
  updateGroups: PropTypes.func,
  history: PropTypes.shape({
    push: PropTypes.func,
  }),
};

export default CreateGroup;
