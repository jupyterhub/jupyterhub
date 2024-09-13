import React from "react";
import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";
import { createStore } from "redux";
import { compose } from "recompose";
import { initialState, reducers } from "./Store";
import withAPI from "./util/withAPI";
import { HashRouter, Routes, Route } from "react-router-dom";

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
          <Routes>
            <Route path="/" element={compose(withAPI)(ServerDashboard)()} />
            <Route path="/groups" element={compose(withAPI)(Groups)()} />
            <Route path="/group-edit" element={compose(withAPI)(GroupEdit)()} />
            <Route
              path="/create-group"
              element={compose(withAPI)(CreateGroup)()}
            />
            <Route path="/add-users" element={compose(withAPI)(AddUser)()} />
            <Route path="/edit-user" element={compose(withAPI)(EditUser)()} />
          </Routes>
        </HashRouter>
      </Provider>
    </div>
  );
};

const root = createRoot(document.getElementById("react-admin-hook"));
root.render(<App />);
