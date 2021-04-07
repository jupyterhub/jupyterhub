import React, { useState } from "react";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

const EditUser = (props) => {
  var {
    editUser,
    deleteUser,
    failRegexEvent,
    refreshUserData,
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
                      onChange={(e) => setAdmin(!admin)}
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
                            history.push("/");
                            refreshUserData();
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
                    if (updatedUsername == "" && admin == has_admin) return;
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
                          history.push("/");
                          refreshUserData();
                        })
                        .catch((err) => {});
                    } else {
                      setUpdatedUsername(null);
                      failRegexEvent();
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
  refreshUserData: PropTypes.func,
};

export default EditUser;
