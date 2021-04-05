import React, { Component } from "react";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

export class AddUser extends Component {
  static get propTypes() {
    return {
      addUsers: PropTypes.func,
      failRegexEvent: PropTypes.func,
      refreshUserData: PropTypes.func,
      dispatch: PropTypes.func,
      history: PropTypes.shape({
        push: PropTypes.func,
      }),
    };
  }

  constructor(props) {
    super(props);
    this.state = {
      users: [],
      admin: false,
    };
  }

  render() {
    var { addUsers, failRegexEvent, refreshUserData, dispatch } = this.props;

    return (
      <>
        <div className="container">
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
                          this.setState(
                            Object.assign({}, this.state, {
                              users: split_users,
                            })
                          );
                        }}
                      ></textarea>
                      <br></br>
                      <input
                        className="form-check-input"
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
                      let filtered_users = this.state.users.filter(
                        (e) =>
                          e.length > 2 &&
                          /[!@#$%^&*(),.?":{}|<>]/g.test(e) == false
                      );
                      if (filtered_users.length < this.state.users.length) {
                        let removed_users = this.state.users.filter(
                          (e) => !filtered_users.includes(e)
                        );
                        this.setState(
                          Object.assign({}, this.state, {
                            users: filtered_users,
                          })
                        );
                        failRegexEvent();
                      }

                      addUsers(filtered_users, this.state.admin)
                        .then(() => refreshUserData())
                        .then(() => this.props.history.push("/"))
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
  }
}
