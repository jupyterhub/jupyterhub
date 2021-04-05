import React, { Component } from "react";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

export class EditUser extends Component {
  static get propTypes() {
    return {
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
  }

  constructor(props) {
    super(props);
    this.state = {
      updated_username: null,
      admin: null,
    };
  }

  render() {
    if (this.props.location.state == undefined) {
      this.props.history.push("/");
      return <></>;
    }

    var { username, has_admin } = this.props.location.state;

    var { editUser, deleteUser, failRegexEvent, refreshUserData } = this.props;

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
                        onKeyDown={(e) => {
                          this.setState(
                            Object.assign({}, this.state, {
                              updated_username: e.target.value,
                            })
                          );
                        }}
                      ></textarea>
                      <br></br>
                      <input
                        className="form-check-input"
                        checked={has_admin ? true : false}
                        type="checkbox"
                        value=""
                        id="admin-check"
                        onChange={(e) =>
                          this.setState(
                            Object.assign({}, this.state, {
                              admin: e.target.checked,
                            })
                          )
                        }
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
                              this.props.history.push("/");
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
                      let updated_username = this.state.updated_username,
                        admin = this.state.admin;

                      if (updated_username == null && admin == null) return;
                      if (
                        updated_username.length > 2 &&
                        /[!@#$%^&*(),.?":{}|<>]/g.test(updated_username) ==
                          false
                      ) {
                        editUser(
                          username,
                          updated_username != null
                            ? updated_username
                            : username,
                          admin != null ? admin : has_admin
                        )
                          .then((data) => {
                            this.props.history.push("/");
                            refreshUserData();
                          })
                          .catch((err) => {});
                      } else {
                        this.setState(
                          Object.assign({}, this.state, {
                            updated_username: "",
                          })
                        );
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
  }
}
