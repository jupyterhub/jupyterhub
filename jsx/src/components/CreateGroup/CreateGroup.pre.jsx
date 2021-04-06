import React, { Component } from "react";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";
import Multiselect from "../Multiselect/Multiselect";

export class CreateGroup extends Component {
  static get propTypes() {
    return {
      createGroup: PropTypes.func,
      refreshGroupsData: PropTypes.func,
      failRegexEvent: PropTypes.func,
      history: PropTypes.shape({
        push: PropTypes.func,
      }),
    };
  }

  constructor(props) {
    super(props);
    this.state = {
      groupName: "",
    };
  }

  render() {
    var { createGroup, refreshGroupsData } = this.props;

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
                      value={this.state.groupName}
                      id="group-name"
                      placeholder="group name..."
                      onChange={(e) => {
                        this.setState({ groupName: e.target.value });
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
                      let groupName = this.state.groupName;
                      createGroup(groupName)
                        .then(refreshGroupsData())
                        .then(this.props.history.push("/groups"))
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
