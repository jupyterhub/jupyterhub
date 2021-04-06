import React, { Component } from "react";
import { Link } from "react-router-dom";
import Multiselect from "../Multiselect/Multiselect";
import PropTypes from "prop-types";

export class GroupEdit extends Component {
  static get propTypes() {
    return {
      location: PropTypes.shape({
        state: PropTypes.shape({
          group_data: PropTypes.object,
          user_data: PropTypes.array,
          callback: PropTypes.func,
        }),
      }),
      history: PropTypes.shape({
        push: PropTypes.func,
      }),
      addToGroup: PropTypes.func,
      removeFromGroup: PropTypes.func,
      deleteGroup: PropTypes.func
    };
  }

  constructor(props) {
    super(props);
    this.state = {
      selected: [],
      changed: false,
      added: undefined,
      removed: undefined,
    };
  }

  render() {
    if (!this.props.location.state) {
      this.props.history.push("/groups");
      return <></>;
    }

    var { group_data, user_data, callback } = this.props.location.state;

    var { addToGroup, removeFromGroup, deleteGroup, refreshGroupsData } = this.props;

    if (!(group_data && user_data)) return <div></div>;

    return (
      <div className="container">
        <div className="row">
          <div className="col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2">
            <h3>Editing Group {group_data.name}</h3>
            <br></br>
            <div className="alert alert-info">Select group members</div>
            <Multiselect
              options={user_data.map((e) => e.name)}
              value={group_data.users}
              onChange={(selection, options) => {
                this.setState({ selected: selection, changed: true });
              }}
            />
            <br></br>
            <button id="return" className="btn btn-light">
              <Link to="/groups">Back</Link>
            </button>
            <span> </span>
            <button
              id="submit"
              className="btn btn-primary"
              onClick={() => {
                // check for changes
                if (!this.state.changed) {
                  this.props.history.push("/groups");
                  return;
                }

                let new_users = this.state.selected.filter(
                  (e) => !group_data.users.includes(e)
                );
                let removed_users = group_data.users.filter(
                  (e) => !this.state.selected.includes(e)
                );

                this.setState(
                  Object.assign({}, this.state, {
                    added: new_users,
                    removed: removed_users,
                  })
                );

                let promiseQueue = [];
                if (new_users.length > 0)
                  promiseQueue.push(addToGroup(new_users, group_data.name));
                if (removed_users.length > 0)
                  promiseQueue.push(
                    removeFromGroup(removed_users, group_data.name)
                  );

                Promise.all(promiseQueue)
                  .then((e) => callback())
                  .catch((err) => console.log(err));

                this.props.history.push("/groups");
              }}
            >
              Apply
            </button>
            <button className="btn btn-danger" style={{ float: "right" }} onClick={() => {
              var groupName = group_data.name
              deleteGroup(groupName)
                .then(refreshGroupsData())
                .then(this.props.history.push("/groups"))
                .catch(err => console.log(err))
            }}>Delete Group</button>
            <br></br>
            <br></br>
          </div>
        </div>
      </div>
    );
  }
}
