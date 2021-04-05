import { connect } from "react-redux";
import { compose, withProps } from "recompose";
import { jhapiRequest } from "../../util/jhapiUtil";
import { GroupEdit } from "./GroupEdit.pre";

const withGroupsAPI = withProps((props) => ({
  addToGroup: (users, groupname) =>
    jhapiRequest("/groups/" + groupname + "/users", "POST", { users }),
  removeFromGroup: (users, groupname) =>
    jhapiRequest("/groups/" + groupname + "/users", "DELETE", { users }),
}));

export default compose(connect(), withGroupsAPI)(GroupEdit);
