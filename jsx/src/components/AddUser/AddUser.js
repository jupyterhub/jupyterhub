import { connect } from "react-redux";
import { compose, withProps } from "recompose";
import { jhapiRequest } from "../../util/jhapiUtil";
import { AddUser } from "./AddUser.pre";

const withUserAPI = withProps((props) => ({
  addUsers: (usernames, admin) =>
    jhapiRequest("/users", "POST", { usernames, admin }),
  failRegexEvent: () =>
    alert(
      "Removed " +
        JSON.stringify(removed_users) +
        " for either containing special characters or being too short."
    ),
  refreshUserData: () =>
    jhapiRequest("/users", "GET")
      .then((data) => data.json())
      .then((data) => props.dispatch({ type: "USER_DATA", value: data })),
}));

export default compose(connect(), withUserAPI)(AddUser);
