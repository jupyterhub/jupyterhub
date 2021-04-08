import { connect } from "react-redux";
import { compose, withProps } from "recompose";
import { jhapiRequest } from "../../util/jhapiUtil";
import GroupEdit from "./GroupEdit.pre";

const withGroupsAPI = withProps((props) => ({
  addToGroup: (users, groupname) =>
    jhapiRequest("/groups/" + groupname + "/users", "POST", { users }),
  removeFromGroup: (users, groupname) =>
    jhapiRequest("/groups/" + groupname + "/users", "DELETE", { users }),
  deleteGroup: (name) => jhapiRequest("/groups/" + name, "DELETE"),
  refreshGroupsData: () =>
    jhapiRequest("/groups", "GET")
      .then((data) => data.json())
      .then((data) => props.dispatch({ type: "GROUPS_DATA", value: data })),
}));

export default compose(connect(), withGroupsAPI)(GroupEdit);
