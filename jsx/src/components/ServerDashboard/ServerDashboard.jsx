import React, { useEffect, useState, Fragment } from "react";
import { useSelector, useDispatch } from "react-redux";
import { debounce } from "lodash";
import PropTypes from "prop-types";

import {
  Button,
  Col,
  Row,
  FormControl,
  Card,
  CardGroup,
  Collapse,
} from "react-bootstrap";
import ReactObjectTableViewer from "../ReactObjectTableViewer/ReactObjectTableViewer";

import { Link } from "react-router-dom";
import { FaSort, FaSortUp, FaSortDown } from "react-icons/fa";

import "./server-dashboard.css";
import { timeSince } from "../../util/timeSince";
import PaginationFooter from "../PaginationFooter/PaginationFooter";

const AccessServerButton = ({ url }) => (
  <a href={url || ""}>
    <button className="btn btn-primary btn-xs" style={{ marginRight: 20 }}>
      Access Server
    </button>
  </a>
);

const RowListItem = ({ text }) => (
  <span className="server-dashboard-row-list-item">{text}</span>
);
RowListItem.propTypes = {
  text: PropTypes.string,
};

const ServerDashboard = (props) => {
  let base_url = window.base_url || "/";
  // sort methods
  var usernameDesc = (e) => e.sort((a, b) => (a.name > b.name ? 1 : -1)),
    usernameAsc = (e) => e.sort((a, b) => (a.name < b.name ? 1 : -1)),
    adminDesc = (e) => e.sort((a) => (a.admin ? -1 : 1)),
    adminAsc = (e) => e.sort((a) => (a.admin ? 1 : -1)),
    dateDesc = (e) =>
      e.sort((a, b) =>
        new Date(a.last_activity) - new Date(b.last_activity) > 0 ? -1 : 1,
      ),
    dateAsc = (e) =>
      e.sort((a, b) =>
        new Date(a.last_activity) - new Date(b.last_activity) > 0 ? 1 : -1,
      ),
    runningAsc = (e) => e.sort((a) => (a.server == null ? -1 : 1)),
    runningDesc = (e) => e.sort((a) => (a.server == null ? 1 : -1));

  var [errorAlert, setErrorAlert] = useState(null);
  var [sortMethod, setSortMethod] = useState(null);
  var [disabledButtons, setDisabledButtons] = useState({});
  var [collapseStates, setCollapseStates] = useState({});

  var user_data = useSelector((state) => state.user_data),
    user_page = useSelector((state) => state.user_page),
    name_filter = useSelector((state) => state.name_filter);

  var offset = user_page ? user_page.offset : 0;
  var limit = user_page ? user_page.limit : window.api_page_limit;
  var total = user_page ? user_page.total : undefined;

  const dispatch = useDispatch();

  var {
    updateUsers,
    shutdownHub,
    startServer,
    stopServer,
    deleteServer,
    startAll,
    stopAll,
    history,
  } = props;

  const dispatchPageUpdate = (data, page) => {
    dispatch({
      type: "USER_PAGE",
      value: {
        data: data,
        page: page,
      },
    });
  };

  const setOffset = (newOffset) => {
    dispatch({
      type: "USER_OFFSET",
      value: {
        offset: newOffset,
      },
    });
  };

  const setNameFilter = (name_filter) => {
    dispatch({
      type: "USER_NAME_FILTER",
      value: {
        name_filter: name_filter,
      },
    });
  };

  useEffect(() => {
    updateUsers(offset, limit, name_filter)
      .then((data) => dispatchPageUpdate(data.items, data._pagination))
      .catch((err) => setErrorAlert("Failed to update user list."));
  }, [offset, limit, name_filter]);

  if (!user_data || !user_page) {
    return <div data-testid="no-show"></div>;
  }

  var slice = [offset, limit, name_filter];

  const handleSearch = debounce(async (event) => {
    setNameFilter(event.target.value);
  }, 300);

  if (sortMethod != null) {
    user_data = sortMethod(user_data);
  }

  const StopServerButton = ({ serverName, userName }) => {
    var [isDisabled, setIsDisabled] = useState(false);
    return (
      <button
        className="btn btn-danger btn-xs stop-button"
        disabled={isDisabled}
        onClick={() => {
          setIsDisabled(true);
          stopServer(userName, serverName)
            .then((res) => {
              if (res.status < 300) {
                updateUsers(...slice)
                  .then((data) => {
                    dispatchPageUpdate(
                      data.items,
                      data._pagination,
                      name_filter,
                    );
                  })
                  .catch(() => {
                    setIsDisabled(false);
                    setErrorAlert(`Failed to update users list.`);
                  });
              } else {
                setErrorAlert(`Failed to stop server.`);
                setIsDisabled(false);
              }
              return res;
            })
            .catch(() => {
              setErrorAlert(`Failed to stop server.`);
              setIsDisabled(false);
            });
        }}
      >
        Stop Server
      </button>
    );
  };

  const DeleteServerButton = ({ serverName, userName }) => {
    if (serverName === "") {
      return null;
    }
    var [isDisabled, setIsDisabled] = useState(false);
    return (
      <button
        className="btn btn-danger btn-xs stop-button"
        // It's not possible to delete unnamed servers
        disabled={isDisabled}
        onClick={() => {
          setIsDisabled(true);
          deleteServer(userName, serverName)
            .then((res) => {
              if (res.status < 300) {
                updateUsers(...slice)
                  .then((data) => {
                    dispatchPageUpdate(
                      data.items,
                      data._pagination,
                      name_filter,
                    );
                  })
                  .catch(() => {
                    setIsDisabled(false);
                    setErrorAlert(`Failed to update users list.`);
                  });
              } else {
                setErrorAlert(`Failed to delete server.`);
                setIsDisabled(false);
              }
              return res;
            })
            .catch(() => {
              setErrorAlert(`Failed to delete server.`);
              setIsDisabled(false);
            });
        }}
      >
        Delete Server
      </button>
    );
  };

  const StartServerButton = ({ serverName, userName }) => {
    var [isDisabled, setIsDisabled] = useState(false);
    return (
      <button
        className="btn btn-success btn-xs start-button"
        disabled={isDisabled}
        onClick={() => {
          setIsDisabled(true);
          startServer(userName, serverName)
            .then((res) => {
              if (res.status < 300) {
                updateUsers(...slice)
                  .then((data) => {
                    dispatchPageUpdate(
                      data.items,
                      data._pagination,
                      name_filter,
                    );
                  })
                  .catch(() => {
                    setErrorAlert(`Failed to update users list.`);
                    setIsDisabled(false);
                  });
              } else {
                setErrorAlert(`Failed to start server.`);
                setIsDisabled(false);
              }
              return res;
            })
            .catch(() => {
              setErrorAlert(`Failed to start server.`);
              setIsDisabled(false);
            });
        }}
      >
        Start Server
      </button>
    );
  };

  const EditUserCell = ({ user }) => {
    return (
      <td>
        <button
          className="btn btn-primary btn-xs"
          style={{ marginRight: 20 }}
          onClick={() =>
            history.push({
              pathname: "/edit-user",
              state: {
                username: user.name,
                has_admin: user.admin,
              },
            })
          }
        >
          Edit User
        </button>
      </td>
    );
  };

  const ServerRowTable = ({ data }) => {
    const sortedData = Object.keys(data)
      .sort()
      .reduce(function (result, key) {
        let value = data[key];
        switch (key) {
          case "last_activity":
          case "created":
          case "started":
            // format timestamps
            value = value ? timeSince(value) : value;
            break;
        }
        if (Array.isArray(value)) {
          value = (
            <Fragment>
              {value.sort().flatMap((v) => (
                <RowListItem text={v} />
              ))}
            </Fragment>
          );
        }
        result[key] = value;
        return result;
      }, {});
    return (
      <ReactObjectTableViewer
        className="table-striped table-bordered"
        style={{
          padding: "3px 6px",
          margin: "auto",
        }}
        keyStyle={{
          padding: "4px",
        }}
        valueStyle={{
          padding: "4px",
        }}
        data={sortedData}
      />
    );
  };

  const serverRow = (user, server) => {
    const { servers, ...userNoServers } = user;
    const serverNameDash = server.name ? `-${server.name}` : "";
    const userServerName = user.name + serverNameDash;
    const open = collapseStates[userServerName] || false;
    return [
      <tr
        key={`${userServerName}-row`}
        data-testid={`user-row-${userServerName}`}
        className="user-row"
      >
        <td data-testid="user-row-name">
          <span>
            <Button
              onClick={() =>
                setCollapseStates({
                  ...collapseStates,
                  [userServerName]: !open,
                })
              }
              aria-controls={`${userServerName}-collapse`}
              aria-expanded={open}
              data-testid={`${userServerName}-collapse-button`}
              variant={open ? "secondary" : "primary"}
              size="sm"
            >
              <span className="caret"></span>
            </Button>{" "}
          </span>
          <span data-testid={`user-name-div-${userServerName}`}>
            {user.name}
          </span>
        </td>
        <td data-testid="user-row-admin">{user.admin ? "admin" : ""}</td>

        <td data-testid="user-row-server">
          <p className="text-secondary">{server.name}</p>
        </td>
        <td data-testid="user-row-last-activity">
          {server.last_activity ? timeSince(server.last_activity) : "Never"}
        </td>
        <td data-testid="user-row-server-activity">
          {server.ready ? (
            // Stop Single-user server
            <>
              <StopServerButton serverName={server.name} userName={user.name} />
              <AccessServerButton url={server.url} />
            </>
          ) : (
            // Start Single-user server
            <>
              <StartServerButton
                serverName={server.name}
                userName={user.name}
                style={{ marginRight: 20 }}
              />
              <DeleteServerButton
                serverName={server.name}
                userName={user.name}
              />
              <a
                href={`${base_url}spawn/${user.name}${
                  server.name ? "/" + server.name : ""
                }`}
              >
                <button
                  className="btn btn-secondary btn-xs"
                  style={{ marginRight: 20 }}
                >
                  Spawn Page
                </button>
              </a>
            </>
          )}
        </td>
        <EditUserCell user={user} />
      </tr>,
      <tr>
        <td
          colSpan={6}
          style={{ padding: 0 }}
          data-testid={`${userServerName}-td`}
        >
          <Collapse in={open} data-testid={`${userServerName}-collapse`}>
            <CardGroup
              id={`${userServerName}-card-group`}
              style={{ width: "100%", margin: "0 auto", float: "none" }}
            >
              <Card style={{ width: "100%", padding: 3, margin: "0 auto" }}>
                <Card.Title>User</Card.Title>
                <ServerRowTable data={userNoServers} />
              </Card>
              <Card style={{ width: "100%", padding: 3, margin: "0 auto" }}>
                <Card.Title>Server</Card.Title>
                <ServerRowTable data={server} />
              </Card>
            </CardGroup>
          </Collapse>
        </td>
      </tr>,
    ];
  };

  let servers = user_data.flatMap((user) => {
    let userServers = Object.values({
      "": user.server || {},
      ...(user.servers || {}),
    });
    return userServers.map((server) => [user, server]);
  });

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
      <div className="server-dashboard-container">
        <Row>
          <Col md={4}>
            <FormControl
              type="text"
              name="user_search"
              placeholder="Search users"
              aria-label="user-search"
              defaultValue={name_filter}
              onChange={handleSearch}
            />
          </Col>

          <Col md="auto" style={{ float: "right", margin: 15 }}>
            <Link to="/groups">{"> Manage Groups"}</Link>
          </Col>
        </Row>
        <table className="table table-bordered table-hover">
          <thead className="admin-table-head">
            <tr>
              <th id="user-header">
                User{" "}
                <SortHandler
                  sorts={{ asc: usernameAsc, desc: usernameDesc }}
                  callback={(method) => setSortMethod(() => method)}
                  testid="user-sort"
                />
              </th>
              <th id="admin-header">
                Admin{" "}
                <SortHandler
                  sorts={{ asc: adminAsc, desc: adminDesc }}
                  callback={(method) => setSortMethod(() => method)}
                  testid="admin-sort"
                />
              </th>
              <th id="server-header">
                Server{" "}
                <SortHandler
                  sorts={{ asc: usernameAsc, desc: usernameDesc }}
                  callback={(method) => setSortMethod(() => method)}
                  testid="server-sort"
                />
              </th>
              <th id="last-activity-header">
                Last Activity{" "}
                <SortHandler
                  sorts={{ asc: dateAsc, desc: dateDesc }}
                  callback={(method) => setSortMethod(() => method)}
                  testid="last-activity-sort"
                />
              </th>
              <th id="running-status-header">
                Running{" "}
                <SortHandler
                  sorts={{ asc: runningAsc, desc: runningDesc }}
                  callback={(method) => setSortMethod(() => method)}
                  testid="running-status-sort"
                />
              </th>
              <th id="actions-header">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr className="noborder">
              <td>
                <Button variant="light" className="add-users-button">
                  <Link to="/add-users">Add Users</Link>
                </Button>
              </td>
              <td></td>
              <td></td>
              <td>
                {/* Start all servers */}
                <Button
                  variant="primary"
                  className="start-all"
                  data-testid="start-all"
                  onClick={() => {
                    Promise.all(startAll(user_data.map((e) => e.name)))
                      .then((res) => {
                        let failedServers = res.filter((e) => !e.ok);
                        if (failedServers.length > 0) {
                          setErrorAlert(
                            `Failed to start ${failedServers.length} ${
                              failedServers.length > 1 ? "servers" : "server"
                            }. ${
                              failedServers.length > 1 ? "Are they " : "Is it "
                            } already running?`,
                          );
                        }
                        return res;
                      })
                      .then((res) => {
                        updateUsers(...slice)
                          .then((data) => {
                            dispatchPageUpdate(
                              data.items,
                              data._pagination,
                              name_filter,
                            );
                          })
                          .catch(() =>
                            setErrorAlert(`Failed to update users list.`),
                          );
                        return res;
                      })
                      .catch(() => setErrorAlert(`Failed to start servers.`));
                  }}
                >
                  Start All
                </Button>
                <span> </span>
                {/* Stop all servers */}
                <Button
                  variant="danger"
                  className="stop-all"
                  data-testid="stop-all"
                  onClick={() => {
                    Promise.all(stopAll(user_data.map((e) => e.name)))
                      .then((res) => {
                        let failedServers = res.filter((e) => !e.ok);
                        if (failedServers.length > 0) {
                          setErrorAlert(
                            `Failed to stop ${failedServers.length} ${
                              failedServers.length > 1 ? "servers" : "server"
                            }. ${
                              failedServers.length > 1 ? "Are they " : "Is it "
                            } already stopped?`,
                          );
                        }
                        return res;
                      })
                      .then((res) => {
                        updateUsers(...slice)
                          .then((data) => {
                            dispatchPageUpdate(
                              data.items,
                              data._pagination,
                              name_filter,
                            );
                          })
                          .catch(() =>
                            setErrorAlert(`Failed to update users list.`),
                          );
                        return res;
                      })
                      .catch(() => setErrorAlert(`Failed to stop servers.`));
                  }}
                >
                  Stop All
                </Button>
              </td>
              <td>
                {/* Shutdown Jupyterhub */}
                <Button
                  variant="danger"
                  id="shutdown-button"
                  onClick={shutdownHub}
                >
                  Shutdown Hub
                </Button>
              </td>
            </tr>
            {servers.flatMap(([user, server]) => serverRow(user, server))}
          </tbody>
        </table>
        <PaginationFooter
          offset={offset}
          limit={limit}
          visible={user_data.length}
          total={total}
          next={() => setOffset(offset + limit)}
          prev={() => setOffset(offset - limit)}
        />
        <br></br>
      </div>
    </div>
  );
};

ServerDashboard.propTypes = {
  user_data: PropTypes.array,
  updateUsers: PropTypes.func,
  shutdownHub: PropTypes.func,
  startServer: PropTypes.func,
  stopServer: PropTypes.func,
  deleteServer: PropTypes.func,
  startAll: PropTypes.func,
  stopAll: PropTypes.func,
  dispatch: PropTypes.func,
  history: PropTypes.shape({
    push: PropTypes.func,
  }),
  location: PropTypes.shape({
    search: PropTypes.string,
  }),
};

const SortHandler = (props) => {
  var { sorts, callback, testid } = props;

  var [direction, setDirection] = useState(undefined);

  return (
    <div
      className="sort-icon"
      data-testid={testid}
      onClick={() => {
        if (!direction) {
          callback(sorts.desc);
          setDirection("desc");
        } else if (direction == "asc") {
          callback(sorts.desc);
          setDirection("desc");
        } else {
          callback(sorts.asc);
          setDirection("asc");
        }
      }}
    >
      {!direction ? (
        <FaSort />
      ) : direction == "asc" ? (
        <FaSortDown />
      ) : (
        <FaSortUp />
      )}
    </div>
  );
};

SortHandler.propTypes = {
  sorts: PropTypes.object,
  callback: PropTypes.func,
  testid: PropTypes.string,
};

export default ServerDashboard;
