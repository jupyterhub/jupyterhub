import React from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import { Link } from "react-router-dom";
import PaginationFooter from "../PaginationFooter/PaginationFooter";

const Groups = (props) => {
  var user_data = useSelector((state) => state.user_data),
    groups_data = useSelector((state) => state.groups_data),
    groups_page = useSelector((state) => state.groups_page),
    limit = useSelector((state) => state.limit),
    dispatch = useDispatch(),
    page = parseInt(new URLSearchParams(props.location.search).get("page"));

  page = isNaN(page) ? 0 : page;
  var slice = [page * limit, limit];

  var { updateGroups, history } = props;

  if (!groups_data || !user_data) {
    return <div></div>;
  }

  const dispatchPageChange = (data, page) => {
    dispatch({
      type: "GROUPS_PAGE",
      value: {
        data: data,
        page: page,
      },
    });
  };

  if (groups_page != page) {
    updateGroups(...slice).then((data) => {
      dispatchPageChange(data, page);
    });
  }

  return (
    <div className="container">
      <div className="row">
        <div className="col-md-12 col-lg-10 col-lg-offset-1">
          <div className="panel panel-default">
            <div className="panel-heading">
              <h4>Groups</h4>
            </div>
            <div className="panel-body">
              <ul className="list-group">
                {groups_data.length > 0 ? (
                  groups_data.map((e, i) => (
                    <li className="list-group-item" key={"group-item" + i}>
                      <span className="badge badge-pill badge-success">
                        {e.users.length + " users"}
                      </span>
                      <Link
                        to={{
                          pathname: "/group-edit",
                          state: {
                            group_data: e,
                            user_data: user_data,
                          },
                        }}
                      >
                        {e.name}
                      </Link>
                    </li>
                  ))
                ) : (
                  <div>
                    <h4>no groups created...</h4>
                  </div>
                )}
              </ul>
              <PaginationFooter
                endpoint="/groups"
                page={page}
                limit={limit}
                numOffset={slice[0]}
                numElements={groups_data.length}
              />
            </div>
            <div className="panel-footer">
              <button className="btn btn-light adjacent-span-spacing">
                <Link to="/">Back</Link>
              </button>
              <button
                className="btn btn-primary adjacent-span-spacing"
                onClick={() => {
                  history.push("/create-group");
                }}
              >
                New Group
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

Groups.propTypes = {
  user_data: PropTypes.array,
  groups_data: PropTypes.array,
  updateUsers: PropTypes.func,
  updateGroups: PropTypes.func,
  history: PropTypes.shape({
    push: PropTypes.func,
  }),
  location: PropTypes.shape({
    search: PropTypes.string,
  }),
};

export default Groups;
