import React, { useState } from "react";
import PropTypes from "prop-types";
import "./group-select.css";

const GroupSelect = (props) => {
  var { onChange, validateUser, users } = props;

  var [selected, setSelected] = useState(users);
  var [username, setUsername] = useState("");
  var [error, setError] = useState(null);

  if (!users) return null;

  return (
    <div className="row">
      {error != null ? (
        <div className="col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2 text-left">
          <div className="alert alert-danger">{error}</div>
        </div>
      ) : (
        <></>
      )}
      <div className="col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2 text-left">
        <div className="input-group">
          <input
            id="username-input"
            type="text"
            className="form-control"
            placeholder="Add by username"
            value={username}
            onChange={(e) => {
              setUsername(e.target.value);
            }}
          />
          <span className="input-group-btn">
            <button
              id="validate-user"
              className="btn btn-default"
              type="button"
              onClick={() => {
                validateUser(username).then((exists) => {
                  if (exists && !selected.includes(username)) {
                    let updated_selection = selected.concat([username]);
                    onChange(updated_selection, users);
                    setUsername("");
                    setSelected(updated_selection);
                    if (error != null) setError(null);
                  } else if (!exists) {
                    setError(`"${username}" is not a valid JupyterHub user.`);
                  }
                });
              }}
            >
              Add user
            </button>
          </span>
        </div>
      </div>
      <div className="col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2 text-left">
        <div className="users-container">
          <hr></hr>
          <div>
            {selected.map((e, i) => (
              <div
                key={"selected" + i}
                className="item selected"
                onClick={() => {
                  let updated_selection = selected
                    .slice(0, i)
                    .concat(selected.slice(i + 1));
                  onChange(updated_selection, users);
                  setSelected(updated_selection);
                }}
              >
                {e}
              </div>
            ))}
            {users.map((e, i) =>
              selected.includes(e) ? undefined : (
                <div
                  key={"unselected" + i}
                  className="item unselected"
                  onClick={() => {
                    let updated_selection = selected.concat([e]);
                    onChange(updated_selection, users);
                    setSelected(updated_selection);
                  }}
                >
                  {e}
                </div>
              )
            )}
          </div>
        </div>
        <br></br>
        <br></br>
      </div>
    </div>
  );
};

GroupSelect.propTypes = {
  onChange: PropTypes.func,
  validateUser: PropTypes.func,
  users: PropTypes.array,
};

export default GroupSelect;
