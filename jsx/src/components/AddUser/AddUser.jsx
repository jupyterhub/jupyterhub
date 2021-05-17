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

  var { addUsers, failRegexEvent, updateUsers, history } = props;

  return (
    <>
      <div className="container">
        {errorAlert != null ? (
          <div className="row">
            <div className="col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2">
              <div className="alert alert-danger">{errorAlert}</div>
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
                      onBlur={(e) => {
                        let split_users = e.target.value.split("\n");
                        setUsers(split_users);
                      }}
                    ></textarea>
                    <br></br>
                    <input
                      className="form-check-input"
                      type="checkbox"
                      value=""
                      id="admin-check"
                      onChange={(e) => setAdmin(e.target.checked)}
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
                  className="btn btn-primary"
                  onClick={() => {
                    let filtered_users = users.filter(
                      (e) =>
                        e.length > 2 &&
                        /[!@#$%^&*(),.?":{}|<>]/g.test(e) == false
                    );
                    if (filtered_users.length < users.length) {
                      setUsers(filtered_users);
                      failRegexEvent();
                    }

                    addUsers(filtered_users, admin)
                      .then((data) =>
                        data.status < 300
                          ? updateUsers(0, limit)
                              .then((data) => dispatchPageChange(data, 0))
                              .then(() => history.push("/"))
                              .catch((err) => console.log(err))
                          : setErrorAlert(
                              `[${data.status}] Failed to create user. ${
                                data.status == 409 ? "User already exists." : ""
                              }`
                            )
                      )
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

AddUser.propTypes = {
  addUsers: PropTypes.func,
  failRegexEvent: PropTypes.func,
  updateUsers: PropTypes.func,
  history: PropTypes.shape({
    push: PropTypes.func,
  }),
};

export default AddUser;
