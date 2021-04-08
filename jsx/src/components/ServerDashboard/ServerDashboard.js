import React, { Component } from "react";
import { compose, withProps, withHandlers } from "recompose";
import { connect } from "react-redux";
import { jhapiRequest } from "../../util/jhapiUtil";
import ServerDashboard from "./ServerDashboard.pre";

const withHubActions = withProps((props) => ({
  updateUsers: (cb) => jhapiRequest("/users", "GET"),
  shutdownHub: () => jhapiRequest("/shutdown", "POST"),
  startServer: (name) => jhapiRequest("/users/" + name + "/server", "POST"),
  stopServer: (name) => jhapiRequest("/users/" + name + "/server", "DELETE"),
  startAll: (names) =>
    names.map((e) => jhapiRequest("/users/" + e + "/server", "POST")),
  stopAll: (names) =>
    names.map((e) => jhapiRequest("/users/" + e + "/server", "DELETE")),
}));

export default compose(
  withHubActions,
  connect((state) => ({ user_data: state.user_data }))
)(ServerDashboard);
