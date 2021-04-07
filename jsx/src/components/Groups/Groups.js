import { compose, withProps } from "recompose";
import { connect } from "react-redux";
import { jhapiRequest } from "../../util/jhapiUtil";
import { Groups } from "./Groups.pre";

const withGroupsAPI = withProps((props) => ({
  refreshGroupsData: () =>
    jhapiRequest("/groups", "GET")
      .then((data) => data.json())
      .then((data) => props.dispatch({ type: "GROUPS_DATA", value: data })),
  refreshUserData: () =>
    jhapiRequest("/users", "GET")
      .then((data) => data.json())
      .then((data) => props.dispatch({ type: "USER_DATA", value: data })),
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

export default compose(
  connect((state) => ({
    user_data: state.user_data,
    groups_data: state.groups_data,
  })),
  withGroupsAPI
)(Groups);
