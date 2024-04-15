import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { Button, Card } from "react-bootstrap";
import PropTypes from "prop-types";
import { MainContainer } from "../../util/layout";

const CreateGroup = (props) => {
  const [groupName, setGroupName] = useState(""),
    [errorAlert, setErrorAlert] = useState(null),
    limit = useSelector((state) => state.limit);

  const dispatch = useDispatch();
  const navigate = useNavigate();

  const dispatchPageUpdate = (data, page) => {
    dispatch({
      type: "GROUPS_PAGE",
      value: {
        data: data,
        page: page,
      },
    });
  };

  const { createGroup, updateGroups } = props;

  return (
    <MainContainer errorAlert={errorAlert} setErrorAlert={setErrorAlert}>
      <Card>
        <Card.Header>
          <h4>Create Group</h4>
        </Card.Header>
        <Card.Body>
          <div className="input-group">
            <input
              className="group-name-input"
              data-testid="group-input"
              type="text"
              id="group-name"
              value={groupName}
              placeholder="group name..."
              onChange={(e) => {
                setGroupName(e.target.value.trim());
              }}
            ></input>
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
              createGroup(groupName)
                .then((data) => {
                  return data.status < 300
                    ? updateGroups(0, limit)
                        .then((data) => dispatchPageUpdate(data, 0))
                        .then(() => navigate("/groups"))
                        .catch(() =>
                          setErrorAlert(`Could not update groups list.`),
                        )
                    : setErrorAlert(
                        `Failed to create group. ${
                          data.status == 409 ? "Group already exists." : ""
                        }`,
                      );
                })
                .catch(() => setErrorAlert(`Failed to create group.`));
            }}
          >
            Create
          </Button>
        </Card.Footer>
      </Card>
    </MainContainer>
  );
};

CreateGroup.propTypes = {
  createGroup: PropTypes.func,
  updateGroups: PropTypes.func,
};

export default CreateGroup;
