import React from "react";
import { useSelector, useDispatch } from "react-redux";
import { compose, withProps } from "recompose";
import PropTypes from "prop-types";

import { Link } from "react-router-dom";
import { jhapiRequest } from "../../util/jhapiUtil";

const Groups = (props) => {
  var user_data = useSelector((state) => state.user_data),
    groups_data = useSelector((state) => state.groups_data),
    dispatch = useDispatch();

  var { refreshGroupsData, refreshUserData, history } = props;

  if (!groups_data || !user_data) {
    return <div></div>;
  }

  const dispatchGroupsData = (data) => {
    dispatch({
      type: "GROUPS_DATA",
      value: data,
    });
  };

  const dispatchUserData = (data) => {
    dispatch({
      type: "USER_DATA",
      value: data,
    });
  };

  return (
    <div className="container">
      <div className="row">
        <div className="col-md-12 col-lg-10 col-lg-offset-1">
          <div className="panel panel-default">
            <div className="panel-heading">
              <h4>Groups</h4>
            </div>
            <div className="panel-body">
              {groups_data.length > 0 ? (
                groups_data.map((e, i) => (
                  <div key={"group-edit" + i} className="group-edit-link">
                    <h4>
                      <Link
                        to={{
                          pathname: "/group-edit",
                          state: {
                            group_data: e,
                            user_data: user_data,
                            callback: () => {
                              refreshGroupsData()
                                .then((data) => dispatchGroupsData(data))
                                .catch((err) => console.log(err));
                              refreshUserData()
                                .then((data) => dispatchUserData(data))
                                .catch((err) => console.log(err));
                            },
                          },
                        }}
                      >
                        {e.name}
                      </Link>
                    </h4>
                  </div>
                ))
              ) : (
                <div>
                  <h4>no groups created...</h4>
                </div>
              )}
            </div>
            <div className="panel-footer">
              <button className="btn btn-light adjacent-span-spacing">
                <Link to="/">Back</Link>
              </button>
              <button
                className="btn btn-primary adjacent-span-spacing"
                onClick={() => {
                  history.push("/create-group");
                }}
              >
                New Group
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

Groups.propTypes = {
  user_data: PropTypes.array,
  groups_data: PropTypes.array,
  refreshUserData: PropTypes.func,
  refreshGroupsData: PropTypes.func,
  history: PropTypes.shape({
    push: PropTypes.func,
  }),
};

const withGroupsAPI = withProps((props) => ({
  refreshGroupsData: () =>
    jhapiRequest("/groups", "GET").then((data) => data.json()),
  refreshUserData: () =>
    jhapiRequest("/users", "GET").then((data) => data.json()),
  addUsersToGroup: (name, new_users) =>
    jhapiRequest("/groups/" + name + "/users", "POST", {
      body: { users: new_users },
      json: true,
    }),
  removeUsersFromGroup: (name, removed_users) =>
    jhapiRequest("/groups/" + name + "/users", "DELETE", {
      body: { users: removed_users },
      json: true,
    }),
}));

export default compose(withGroupsAPI)(Groups);
