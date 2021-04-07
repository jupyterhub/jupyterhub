import React, { Component } from "react";
import ReactDOM from "react-dom";
import { Provider } from "react-redux";
import { createStore } from "redux";
import { Button } from "react-bootstrap";
import { initialState, reducers } from "./Store";
import { jhapiRequest } from "./util/jhapiUtil";
import { HashRouter, Switch, Route, Link } from "react-router-dom";
import { createBrowserHistory } from "history";

import ServerDashboard from "./components/ServerDashboard/ServerDashboard";
import Groups from "./components/Groups/Groups";
import GroupEdit from "./components/GroupEdit/GroupEdit";
import CreateGroup from "./components/CreateGroup/CreateGroup";
import AddUser from "./components/AddUser/AddUser";
import EditUser from "./components/EditUser/EditUser";

import "./style/root.css";

const store = createStore(reducers, initialState),
  routerHistory = createBrowserHistory();

class App extends Component {
  componentDidMount() {
    jhapiRequest("/users", "GET")
      .then((data) => data.json())
      .then((data) => store.dispatch({ type: "USER_DATA", value: data }))
      .catch((err) => console.log(err));

    jhapiRequest("/groups", "GET")
      .then((data) => data.json())
      .then((data) => store.dispatch({ type: "GROUPS_DATA", value: data }))
      .catch((err) => console.log(err));
  }

  render() {
    return (
      <div className="resets">
        <Provider store={store}>
          <HashRouter>
            <Switch>
              <Route exact path="/" component={ServerDashboard} />
              <Route exact path="/groups" component={Groups} />
              <Route exact path="/group-edit" component={GroupEdit} />
              <Route exact path="/create-group" component={CreateGroup} />
              <Route exact path="/add-users" component={AddUser} />
              <Route exact path="/edit-user" component={EditUser} />
            </Switch>
          </HashRouter>
        </Provider>
      </div>
    );
  }
}

ReactDOM.render(<App />, document.getElementById("react-admin-hook"));
