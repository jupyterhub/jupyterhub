import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { Button, Col } from "react-bootstrap";
import PropTypes from "prop-types";
import ErrorAlert from "../../util/error";

const AddUser = (props) => {
  const [users, setUsers] = useState([]),
    [admin, setAdmin] = useState(false),
    [errorAlert, setErrorAlert] = useState(null),
    limit = useSelector((state) => state.limit);

  const dispatch = useDispatch();
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

  var { addUsers, updateUsers } = props;

  return (
    <>
      <div className="container" data-testid="container">
        <ErrorAlert errorAlert={errorAlert} setErrorAlert={setErrorAlert} />
        <div className="row">
          <Col md={{ span: 10, offset: 1 }} lg={{ span: 8, offset: 2 }}>
            <div className="card">
              <div className="card-header">
                <h4>Add Users</h4>
              </div>
              <div className="card-body">
                <form>
                  <div className="form-group">
                    <textarea
                      className="form-control"
                      id="add-user-textarea"
                      rows="3"
                      placeholder="usernames separated by line"
                      data-testid="user-textarea"
                      onBlur={(e) => {
                        let split_users = e.target.value
                          .split("\n")
                          .map((u) => u.trim())
                          .filter((u) => u.length > 0);
                        setUsers(split_users);
                      }}
                    ></textarea>
                    <br></br>
                    <input
                      className="form-check-input"
                      data-testid="check"
                      type="checkbox"
                      id="admin-check"
                      checked={admin}
                      onChange={() => setAdmin(!admin)}
                    />
                    <span> </span>
                    <label className="form-check-label">Admin</label>
                  </div>
                </form>
              </div>
              <div className="card-footer">
                <Link to="/">
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
                    addUsers(users, admin)
                      .then((data) =>
                        data.status < 300
                          ? updateUsers(0, limit)
                              .then((data) => dispatchPageChange(data, 0))
                              .then(() => navigate("/"))
                              .catch(() =>
                                setErrorAlert(`Failed to update users.`),
                              )
                          : setErrorAlert(
                              `Failed to create user. ${
                                data.status == 409 ? "User already exists." : ""
                              }`,
                            ),
                      )
                      .catch(() => setErrorAlert(`Failed to create user.`));
                  }}
                >
                  Add Users
                </Button>
              </div>
            </div>
          </Col>
        </div>
      </div>
    </>
  );
};

AddUser.propTypes = {
  addUsers: PropTypes.func,
  updateUsers: PropTypes.func,
};

export default AddUser;
