import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";

const EditUser = (props) => {
  var limit = useSelector((state) => state.limit),
    [errorAlert, setErrorAlert] = useState(null);

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

  var {
    editUser,
    deleteUser,
    failRegexEvent,
    noChangeEvent,
    updateUsers,
    history,
  } = props;

  if (props.location.state == undefined) {
    props.history.push("/");
    return <></>;
  }

  var { username, has_admin } = props.location.state;

  var [updatedUsername, setUpdatedUsername] = useState(""),
    [admin, setAdmin] = useState(has_admin);

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
                <h4>Editing user {username}</h4>
              </div>
              <div className="panel-body">
                <form>
                  <div className="form-group">
                    <textarea
                      className="form-control"
                      id="exampleFormControlTextarea1"
                      rows="3"
                      placeholder="updated username"
                      onBlur={(e) => {
                        setUpdatedUsername(e.target.value);
                      }}
                    ></textarea>
                    <br></br>
                    <input
                      className="form-check-input"
                      checked={admin}
                      type="checkbox"
                      id="admin-check"
                      onChange={() => setAdmin(!admin)}
                    />
                    <span> </span>
                    <label className="form-check-label">Admin</label>
                    <br></br>
                    <button
                      id="delete-user"
                      className="btn btn-danger btn-sm"
                      onClick={() => {
                        deleteUser(username)
                          .then((data) => {
                            data.status < 300
                              ? updateUsers(0, limit)
                                  .then((data) => dispatchPageChange(data, 0))
                                  .then(() => history.push("/"))
                                  .catch((err) => console.log(err))
                              : setErrorAlert(
                                  `[${data.status}] Failed to edit user.`
                                );
                          })
                          .catch((err) => console.log(err));
                      }}
                    >
                      Delete user
                    </button>
                  </div>
                </form>
              </div>
              <div className="panel-footer">
                <button className="btn btn-light">
                  <Link to="/">Back</Link>
                </button>
                <span> </span>
                <button
                  id="submit"
                  className="btn btn-primary"
                  onClick={() => {
                    if (updatedUsername == "" && admin == has_admin) {
                      noChangeEvent();
                      return;
                    } else if (updatedUsername != "") {
                      if (
                        updatedUsername.length > 2 &&
                        /[!@#$%^&*(),.?":{}|<>]/g.test(updatedUsername) == false
                      ) {
                        editUser(
                          username,
                          updatedUsername != "" ? updatedUsername : username,
                          admin
                        )
                          .then((data) => {
                            data.status < 300
                              ? updateUsers(0, limit)
                                  .then((data) => dispatchPageChange(data, 0))
                                  .then(() => history.push("/"))
                                  .catch((err) => console.log(err))
                              : setErrorAlert(
                                  `[${data.status}] Failed to edit user.`
                                );
                          })
                          .catch((err) => {
                            console.log(err);
                          });
                      } else {
                        setUpdatedUsername("");
                        failRegexEvent();
                      }
                    } else {
                      editUser(username, username, admin)
                        .then((data) => {
                          data.status < 300
                            ? updateUsers(0, limit)
                                .then((data) => dispatchPageChange(data, 0))
                                .then(() => history.push("/"))
                                .catch((err) => console.log(err))
                            : setErrorAlert(
                                `[${data.status}] Failed to edit user.`
                              );
                        })
                        .catch((err) => {
                          console.log(err);
                        });
                    }
                  }}
                >
                  Apply
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

EditUser.propTypes = {
  location: PropTypes.shape({
    state: PropTypes.shape({
      username: PropTypes.string,
      has_admin: PropTypes.bool,
    }),
  }),
  history: PropTypes.shape({
    push: PropTypes.func,
  }),
  editUser: PropTypes.func,
  deleteUser: PropTypes.func,
  failRegexEvent: PropTypes.func,
  noChangeEvent: PropTypes.func,
  updateUsers: PropTypes.func,
};

export default EditUser;
