import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";
import GroupSelect from "../GroupSelect/GroupSelect";
import DynamicTable from "../DynamicTable/DynamicTable";

const GroupEdit = (props) => {
  var [selected, setSelected] = useState([]),
    [changed, setChanged] = useState(false),
    [errorAlert, setErrorAlert] = useState(null),
    limit = useSelector((state) => state.limit);

  var dispatch = useDispatch();
  const hasDuplicates = (a) => a.filter((e, i) => a.indexOf(e) != i).length > 0;
  const dispatchPageUpdate = (data, page) => {
    dispatch({
      type: "GROUPS_PAGE",
      value: {
        data: data,
        page: page,
      },
    });
  };

  var {
    addToGroup,
    updateProp,
    removeFromGroup,
    deleteGroup,
    updateGroups,
    validateUser,
    history,
    location,
  } = props;

  if (!location.state) {
    history.push("/groups");
    return <></>;
  }

  var { group_data } = location.state;
  var [propobject, setProp] = useState(group_data.properties);
  var [propkeys, setPropKeys] = useState([]);
  var [propvalues, setPropValues] = useState([]);

  if (!group_data) return <div></div>;

  return (
    <div className="container" data-testid="container">
      {errorAlert != null ? (
        <div className="row">
          <div className="col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2">
            <div className="alert alert-danger">
              {errorAlert}
              <button
                type="button"
                className="close"
                onClick={() => setErrorAlert(null)}
              >
                <span>&times;</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        <></>
      )}
      <div className="row">
        <div className="col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2">
          <h3>Editing Group {group_data.name}</h3>
          <br></br>
          <div className="alert alert-info">Manage group members</div>
        </div>
      </div>
      <GroupSelect
        users={group_data.users}
        validateUser={validateUser}
        onChange={(selection) => {
          setSelected(selection);
          setChanged(true);
        }}
      />
      <div className="row">
        <div className="col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2">
          <div className="alert alert-info">Manage group properties</div>
        </div>
      </div>
      <div className="row">
        <div className="col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2">
          <DynamicTable
            current_propobject={group_data.properties}
            setProp={setProp}
            setPropKeys={setPropKeys}
            setPropValues={setPropValues}

            //Add keys
          />
        </div>
      </div>

      <div className="row">
        <div className="col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2">
          <button id="return" className="btn btn-light">
            <Link to="/groups">Back</Link>
          </button>
          <span> </span>
          <button
            id="submit"
            data-testid="submit"
            className="btn btn-primary"
            onClick={() => {
              // check for changes
              let new_users = selected.filter(
                (e) => !group_data.users.includes(e),
              );
              let removed_users = group_data.users.filter(
                (e) => !selected.includes(e),
              );
              let promiseQueue = [];
              if (new_users.length > 0)
                promiseQueue.push(addToGroup(new_users, group_data.name));
              if (removed_users.length > 0)
                promiseQueue.push(
                  removeFromGroup(removed_users, group_data.name),
                );

              if (hasDuplicates(propkeys) == true) {
                setErrorAlert(`Duplicate keys found!`);
              } else {
                propkeys.forEach((key, i) => (propobject[key] = propvalues[i]));
              }
              if (
                propobject != group_data.properties &&
                hasDuplicates(propkeys) == false
              ) {
                promiseQueue.push(updateProp(propobject, group_data.name));
                setErrorAlert(null);
              }
              Promise.all(promiseQueue)
                .then((data) => {
                  // ensure status of all requests are < 300
                  let allPassed =
                    data.map((e) => e.status).filter((e) => e >= 300).length ==
                    0;

                  allPassed
                    ? updateGroups(0, limit).then((data) =>
                        dispatchPageUpdate(data, 0),
                      )
                    : setErrorAlert(`Failed to edit group.`);
                })
                .catch(() => {
                  setErrorAlert(`Failed to edit group.`);
                });
            }}
          >
            Apply
          </button>
          <div>
            <span id="error"></span>
          </div>
          <button
            id="delete-group"
            data-testid="delete-group"
            className="btn btn-danger"
            style={{ float: "right" }}
            onClick={() => {
              var groupName = group_data.name;
              deleteGroup(groupName)
                // TODO add error if res not ok
                .then((data) => {
                  data.status < 300
                    ? updateGroups(0, limit)
                        .then((data) => dispatchPageUpdate(data, 0))
                        .then(() => history.push("/groups"))
                    : setErrorAlert(`Failed to delete group.`);
                })
                .catch(() => setErrorAlert(`Failed to delete group.`));
            }}
          >
            Delete Group
          </button>
          <br></br>
          <br></br>
        </div>
      </div>
    </div>
  );
};

GroupEdit.propTypes = {
  location: PropTypes.shape({
    state: PropTypes.shape({
      group_data: PropTypes.object,
      callback: PropTypes.func,
    }),
  }),
  history: PropTypes.shape({
    push: PropTypes.func,
  }),
  addToGroup: PropTypes.func,
  removeFromGroup: PropTypes.func,
  deleteGroup: PropTypes.func,
  updateGroups: PropTypes.func,
  validateUser: PropTypes.func,
};

export default GroupEdit;
