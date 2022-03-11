import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import { Button } from "react-bootstrap";
import { Link } from "react-router-dom";
import { FaSort, FaSortUp, FaSortDown } from "react-icons/fa";

import "./server-dashboard.css";
import { timeSince } from "../../util/timeSince";
import PaginationFooter from "../PaginationFooter/PaginationFooter";

const AccessServerButton = ({ userName, serverName }) => (
  <a href={`/user/${userName}/${serverName || ""}`}>
    <button className="btn btn-primary btn-xs" style={{ marginRight: 20 }}>
      Access Server
    </button>
  </a>
);

const ServerDashboard = (props) => {
  // sort methods
  var usernameDesc = (e) => e.sort((a, b) => (a.name > b.name ? 1 : -1)),
    usernameAsc = (e) => e.sort((a, b) => (a.name < b.name ? 1 : -1)),
    adminDesc = (e) => e.sort((a) => (a.admin ? -1 : 1)),
    adminAsc = (e) => e.sort((a) => (a.admin ? 1 : -1)),
    dateDesc = (e) =>
      e.sort((a, b) =>
        new Date(a.last_activity) - new Date(b.last_activity) > 0 ? -1 : 1
      ),
    dateAsc = (e) =>
      e.sort((a, b) =>
        new Date(a.last_activity) - new Date(b.last_activity) > 0 ? 1 : -1
      ),
    runningAsc = (e) => e.sort((a) => (a.server == null ? -1 : 1)),
    runningDesc = (e) => e.sort((a) => (a.server == null ? 1 : -1));

  var [errorAlert, setErrorAlert] = useState(null);
  var [sortMethod, setSortMethod] = useState(null);
  var [disabledButtons, setDisabledButtons] = useState({});

  var user_data = useSelector((state) => state.user_data),
    user_page = useSelector((state) => state.user_page),
    limit = useSelector((state) => state.limit),
    page = parseInt(new URLSearchParams(props.location.search).get("page"));

  page = isNaN(page) ? 0 : page;
  var slice = [page * limit, limit];

  const dispatch = useDispatch();

  var {
    updateUsers,
    shutdownHub,
    startServer,
    stopServer,
    startAll,
    stopAll,
    history,
  } = props;

  var dispatchPageUpdate = (data, page) => {
    dispatch({
      type: "USER_PAGE",
      value: {
        data: data,
        page: page,
      },
    });
  };

  if (!user_data) {
    return <div data-testid="no-show"></div>;
  }

  if (page != user_page) {
    updateUsers(...slice).then((data) => dispatchPageUpdate(data, page));
  }

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
                    dispatchPageUpdate(data, page);
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
                    dispatchPageUpdate(data, page);
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
      <div className="manage-groups" style={{ float: "right", margin: "20px" }}>
        <Link to="/groups">{"> Manage Groups"}</Link>
      </div>
      <div className="server-dashboard-container">
        <table className="table table-striped table-bordered table-hover">
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
                            } already running?`
                          );
                        }
                        return res;
                      })
                      .then((res) => {
                        updateUsers(...slice)
                          .then((data) => {
                            dispatchPageUpdate(data, page);
                          })
                          .catch(() =>
                            setErrorAlert(`Failed to update users list.`)
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
                            } already stopped?`
                          );
                        }
                        return res;
                      })
                      .then((res) => {
                        updateUsers(...slice)
                          .then((data) => {
                            dispatchPageUpdate(data, page);
                          })
                          .catch(() =>
                            setErrorAlert(`Failed to update users list.`)
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
            {servers.map(([user, server], i) => {
              server.name = server.name || "";
              return (
                <tr key={i + "row"} className="user-row">
                  <td data-testid="user-row-name">{user.name}</td>
                  <td data-testid="user-row-admin">
                    {user.admin ? "admin" : ""}
                  </td>

                  <td data-testid="user-row-server">
                    {server.name ? (
                      <p class="text-secondary">{server.name}</p>
                    ) : (
                      <p style={{ color: "lightgrey" }}>[MAIN]</p>
                    )}
                  </td>
                  <td data-testid="user-row-last-activity">
                    {server.last_activity
                      ? timeSince(server.last_activity)
                      : "Never"}
                  </td>
                  <td data-testid="user-row-server-activity">
                    {server.started ? (
                      // Stop Single-user server
                      <>
                        <StopServerButton
                          serverName={server.name}
                          userName={user.name}
                        />
                        <AccessServerButton
                          serverName={server.name}
                          userName={user.name}
                        />
                      </>
                    ) : (
                      // Start Single-user server
                      <>
                        <StartServerButton
                          serverName={server.name}
                          userName={user.name}
                        />
                        <a
                          href={`/spawn/${user.name}${
                            server.name && "/" + server.name
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
                </tr>
              );
            })}
          </tbody>
        </table>
        <PaginationFooter
          endpoint="/"
          page={page}
          limit={limit}
          numOffset={slice[0]}
          numElements={user_data.length}
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
