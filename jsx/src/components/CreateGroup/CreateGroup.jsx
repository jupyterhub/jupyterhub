import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { Button, Card } from "react-bootstrap";
import PropTypes from "prop-types";

const CreateGroup = (props) => {
  const [groupName, setGroupName] = useState(""),
    [errorAlert, setErrorAlert] = useState(null),
    limit = useSelector((state) => state.limit);

  const dispatch = useDispatch();
  const navigate = useNavigate();

  const dispatchPageUpdate = (data, page) => {
    dispatch({
      type: "GROUPS_PAGE",
      value: {
        data: data,
        page: page,
      },
    });
  };

  const { createGroup, updateGroups } = props;

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
            <div className="card">
              <div className="card-header">
                <h4>Create Group</h4>
              </div>
              <div className="card-body">
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
              <div className="card-footer">
                <Link to="/groups">
                  <Button variant="light" id="return">
                    Back
                  </Button>
                </Link>
                <span> </span>
                <Button
                  id="submit"
                  data-testid="submit"
                  variant="primary"
                  onClick={() => {
                    createGroup(groupName)
                      .then((data) => {
                        return data.status < 300
                          ? updateGroups(0, limit)
                              .then((data) => dispatchPageUpdate(data, 0))
                              .then(() => navigate("/groups"))
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
                </Button>
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
};

export default CreateGroup;
