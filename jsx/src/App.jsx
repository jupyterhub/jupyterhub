import React from "react";
import ReactDOM from "react-dom";
import { Provider } from "react-redux";
import { createStore } from "redux";
import { compose } from "recompose";
import { initialState, reducers } from "./Store";
import withAPI from "./util/withAPI";
import { HashRouter, Switch, Route } from "react-router-dom";

import ServerDashboard from "./components/ServerDashboard/ServerDashboard";
import Groups from "./components/Groups/Groups";
import GroupEdit from "./components/GroupEdit/GroupEdit";
import CreateGroup from "./components/CreateGroup/CreateGroup";
import AddUser from "./components/AddUser/AddUser";
import EditUser from "./components/EditUser/EditUser";

import "./style/root.css";

const store = createStore(reducers, initialState);

const App = () => {
  return (
    <div className="resets">
      <Provider store={store}>
        <HashRouter>
          <Switch>
            <Route
              exact
              path="/"
              component={compose(withAPI)(ServerDashboard)}
            />
            <Route exact path="/groups" component={compose(withAPI)(Groups)} />
            <Route
              exact
              path="/group-edit"
              component={compose(withAPI)(GroupEdit)}
            />
            <Route
              exact
              path="/create-group"
              component={compose(withAPI)(CreateGroup)}
            />
            <Route
              exact
              path="/add-users"
              component={compose(withAPI)(AddUser)}
            />
            <Route
              exact
              path="/edit-user"
              component={compose(withAPI)(EditUser)}
            />
          </Switch>
        </HashRouter>
      </Provider>
    </div>
  );
};

ReactDOM.render(<App />, document.getElementById("react-admin-hook"));
