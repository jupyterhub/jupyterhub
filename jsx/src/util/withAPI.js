import { withProps } from "recompose";
import { jhapiRequest } from "./jhapiUtil";

const withAPI = withProps(() => ({
  updateUsers: (offset, limit) =>
    jhapiRequest(`/users?offset=${offset}&limit=${limit}`, "GET").then((data) =>
      data.json()
    ),
  updateGroups: (offset, limit) =>
    jhapiRequest(`/groups?offset=${offset}&limit=${limit}`, "GET").then(
      (data) => data.json()
    ),
  shutdownHub: () => jhapiRequest("/shutdown", "POST"),
  startServer: (name) => jhapiRequest("/users/" + name + "/server", "POST"),
  stopServer: (name) => jhapiRequest("/users/" + name + "/server", "DELETE"),
  startAll: (names) =>
    names.map((e) => jhapiRequest("/users/" + e + "/server", "POST")),
  stopAll: (names) =>
    names.map((e) => jhapiRequest("/users/" + e + "/server", "DELETE")),
  addToGroup: (users, groupname) =>
    jhapiRequest("/groups/" + groupname + "/users", "POST", { users }),
  removeFromGroup: (users, groupname) =>
    jhapiRequest("/groups/" + groupname + "/users", "DELETE", { users }),
  createGroup: (groupName) => jhapiRequest("/groups/" + groupName, "POST"),
  deleteGroup: (name) => jhapiRequest("/groups/" + name, "DELETE"),
  addUsers: (usernames, admin) =>
    jhapiRequest("/users", "POST", { usernames, admin }),
  editUser: (username, updated_username, admin) =>
    jhapiRequest("/users/" + username, "PATCH", {
      name: updated_username,
      admin,
    }),
  deleteUser: (username) => jhapiRequest("/users/" + username, "DELETE"),
  findUser: (username) => jhapiRequest("/users/" + username, "GET"),
  validateUser: (username) =>
    jhapiRequest("/users/" + username, "GET")
      .then((data) => data.status)
      .then((data) => (data > 200 ? false : true)),
  failRegexEvent: () =>
    alert(
      "Cannot change username - either contains special characters or is too short."
    ),
  noChangeEvent: () => {
    returns;
  },
  refreshGroupsData: () =>
    jhapiRequest("/groups", "GET").then((data) => data.json()),
  refreshUserData: () =>
    jhapiRequest("/users", "GET").then((data) => data.json()),
}));

export default withAPI;
