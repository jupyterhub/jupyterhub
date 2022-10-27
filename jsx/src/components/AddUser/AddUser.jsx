import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

const AddUser = (props) => {
  var [users, setUsers] = useState([]),
    [admin, setAdmin] = useState(false),
    [errorAlert, setErrorAlert] = useState(null),
    limit = useSelector((state) => state.limit);

  var dispatch = useDispatch();

  var dispatchPageChange = (data, page) => {
    dispatch({
      type: "USER_PAGE",
      value: {
        data: data,
        page: page,
      },
    });
  };

  var { addUsers, updateUsers, history } = props;

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
                <h4>Add Users</h4>
              </div>
              <div className="panel-body">
                <form>
                  <div className="form-group">
                    <textarea
                      className="form-control"
                      id="add-user-textarea"
                      rows="3"
                      placeholder="usernames separated by line"
                      data-testid="user-textarea"
                      onBlur={(e) => {
                        let split_users = e.target.value
                          .split("\n")
                          .map((u) => u.trim())
                          .filter((u) => u.length > 0);
                        setUsers(split_users);
                      }}
                    ></textarea>
                    <br></br>
                    <input
                      className="form-check-input"
                      data-testid="check"
                      type="checkbox"
                      id="admin-check"
                      checked={admin}
                      onChange={() => setAdmin(!admin)}
                    />
                    <span> </span>
                    <label className="form-check-label">Admin</label>
                  </div>
                </form>
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
                    addUsers(users, admin)
                      .then((data) =>
                        data.status < 300
                          ? updateUsers(0, limit)
                              .then((data) => dispatchPageChange(data, 0))
                              .then(() => history.push("/"))
                              .catch(() =>
                                setErrorAlert(`Failed to update users.`),
                              )
                          : setErrorAlert(
                              `Failed to create user. ${
                                data.status == 409 ? "User already exists." : ""
                              }`,
                            ),
                      )
                      .catch(() => setErrorAlert(`Failed to create user.`));
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

AddUser.propTypes = {
  addUsers: PropTypes.func,
  updateUsers: PropTypes.func,
  history: PropTypes.shape({
    push: PropTypes.func,
  }),
};

export default AddUser;
