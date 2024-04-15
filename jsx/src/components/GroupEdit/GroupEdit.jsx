import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Link, useNavigate, useLocation } from "react-router-dom";
import PropTypes from "prop-types";
import { Button, Card } from "react-bootstrap";
import GroupSelect from "../GroupSelect/GroupSelect";
import DynamicTable from "../DynamicTable/DynamicTable";
import { MainContainer } from "../../util/layout";

const GroupEdit = (props) => {
  const [selected, setSelected] = useState([]),
    [changed, setChanged] = useState(false),
    [errorAlert, setErrorAlert] = useState(null),
    navigate = useNavigate(),
    location = useLocation(),
    limit = useSelector((state) => state.limit);

  const dispatch = useDispatch();
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

  const {
    addToGroup,
    updateProp,
    removeFromGroup,
    deleteGroup,
    updateGroups,
    validateUser,
  } = props;

  useEffect(() => {
    if (!location.state) {
      navigate("/groups");
    }
  }, [location]);

  const { group_data } = location.state || {};
  if (!group_data) return <div></div>;
  const [propobject, setProp] = useState(group_data.properties);
  const [propkeys, setPropKeys] = useState([]);
  const [propvalues, setPropValues] = useState([]);

  return (
    <MainContainer errorAlert={errorAlert} setErrorAlert={setErrorAlert}>
      <h1>Editing Group {group_data.name}</h1>
      <Card>
        <Card.Header>
          <h2>Manage group members</h2>
        </Card.Header>
        <Card.Body>
          <GroupSelect
            users={group_data.users}
            validateUser={validateUser}
            onChange={(selection) => {
              setSelected(selection);
              setChanged(true);
            }}
          />
        </Card.Body>
        <Card.Header>
          <h2>Manage group properties</h2>
        </Card.Header>
        <Card.Body>
          <DynamicTable
            current_propobject={group_data.properties}
            setProp={setProp}
            setPropKeys={setPropKeys}
            setPropValues={setPropValues}

            //Add keys
          />
          <div>
            <span id="error"></span>
          </div>
        </Card.Body>
        <Card.Footer>
          <Link to="/groups">
            <Button variant="light" id="return">
              Back
            </Button>
          </Link>
          <span> </span>
          <Button
            id="submit"
            data-testid="submit"
            variant="primary"
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
          </Button>
          <Button
            id="delete-group"
            data-testid="delete-group"
            variant="danger"
            className="float-end"
            onClick={() => {
              var groupName = group_data.name;
              deleteGroup(groupName)
                // TODO add error if res not ok
                .then((data) => {
                  data.status < 300
                    ? updateGroups(0, limit)
                        .then((data) => dispatchPageUpdate(data, 0))
                        .then(() => navigate("/groups"))
                    : setErrorAlert(`Failed to delete group.`);
                })
                .catch(() => setErrorAlert(`Failed to delete group.`));
            }}
          >
            Delete Group
          </Button>
          <div>
            <span id="error"></span>
          </div>
        </Card.Footer>
      </Card>
    </MainContainer>
  );
};

GroupEdit.propTypes = {
  addToGroup: PropTypes.func,
  removeFromGroup: PropTypes.func,
  deleteGroup: PropTypes.func,
  updateGroups: PropTypes.func,
  validateUser: PropTypes.func,
};

export default GroupEdit;
