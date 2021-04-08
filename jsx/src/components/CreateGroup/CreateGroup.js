import { connect } from "react-redux";
import { compose, withProps } from "recompose";
import { jhapiRequest } from "../../util/jhapiUtil";
import CreateGroup from "./CreateGroup.pre";

const withUserAPI = withProps((props) => ({
  createGroup: (groupName) => jhapiRequest("/groups/" + groupName, "POST"),
  failRegexEvent: () =>
    alert(
      "Removed " +
        JSON.stringify(removed_users) +
        " for either containing special characters or being too short."
    ),
  refreshGroupsData: () =>
    jhapiRequest("/groups", "GET")
      .then((data) => data.json())
      .then((data) => props.dispatch({ type: "GROUPS_DATA", value: data })),
}));

export default compose(connect(), withUserAPI)(CreateGroup);
