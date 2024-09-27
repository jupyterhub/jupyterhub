import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button, Card } from "react-bootstrap";
import { MainContainer } from "../../util/layout";

const EditUser = (props) => {
  const limit = useSelector((state) => state.limit),
    [errorAlert, setErrorAlert] = useState(null);

  const dispatch = useDispatch();
  const location = useLocation();
  const navigate = useNavigate();

  var dispatchPageChange = (data, page) => {
    dispatch({
      type: "USER_PAGE",
      value: {
        data: data,
        page: page,
      },
    });
  };

  var { editUser, deleteUser, noChangeEvent, updateUsers } = props;

  useEffect(() => {
    if (!location.state) {
      navigate("/");
    }
  }, [location]);

  if (!location.state) {
    return null;
  }

  var { username, has_admin } = location.state;

  var [updatedUsername, setUpdatedUsername] = useState(""),
    [admin, setAdmin] = useState(has_admin);

  return (
    <MainContainer errorAlert={errorAlert} setErrorAlert={setErrorAlert}>
      <Card>
        <Card.Header>
          <h1>Editing user {username}</h1>
        </Card.Header>
        <Card.Body>
          <form>
            <div className="form-group">
              <textarea
                className="form-control"
                data-testid="edit-username-input"
                id="exampleFormControlTextarea1"
                rows="3"
                placeholder="updated username"
                onBlur={(e) => {
                  setUpdatedUsername(e.target.value);
                }}
              ></textarea>
              <br></br>
              <input
                className="form-check-input"
                checked={admin}
                type="checkbox"
                id="admin-check"
                onChange={() => setAdmin(!admin)}
              />
              <span> </span>
              <label className="form-check-label">Admin</label>
            </div>
          </form>
        </Card.Body>
        <Card.Footer>
          <Link to="/">
            <Button variant="light">Back</Button>
          </Link>
          <span> </span>
          <Button
            id="submit"
            data-testid="submit"
            variant="primary"
            onClick={(e) => {
              e.preventDefault();
              if (updatedUsername == "" && admin == has_admin) {
                noChangeEvent();
                return;
              } else {
                editUser(
                  username,
                  updatedUsername != "" ? updatedUsername : username,
                  admin,
                )
                  .then((data) => {
                    data.status < 300
                      ? updateUsers(0, limit)
                          .then((data) => dispatchPageChange(data, 0))
                          .then(() => navigate("/"))
                          .catch(() =>
                            setErrorAlert(`Could not update users list.`),
                          )
                      : setErrorAlert(`Failed to edit user.`);
                  })
                  .catch(() => {
                    setErrorAlert(`Failed to edit user.`);
                  });
              }
            }}
          >
            Apply
          </Button>
          <Button
            id="delete-user"
            data-testid="delete-user"
            variant="danger"
            className="float-end"
            onClick={(e) => {
              e.preventDefault();
              deleteUser(username)
                .then((data) => {
                  data.status < 300
                    ? updateUsers(0, limit)
                        .then((data) => dispatchPageChange(data, 0))
                        .then(() => navigate("/"))
                        .catch(() =>
                          setErrorAlert(`Could not update users list.`),
                        )
                    : setErrorAlert(`Failed to edit user.`);
                })
                .catch(() => {
                  setErrorAlert(`Failed to edit user.`);
                });
            }}
          >
            Delete user
          </Button>
        </Card.Footer>
      </Card>
    </MainContainer>
  );
};

EditUser.propTypes = {
  editUser: PropTypes.func,
  deleteUser: PropTypes.func,
  noChangeEvent: PropTypes.func,
  updateUsers: PropTypes.func,
};

export default EditUser;
