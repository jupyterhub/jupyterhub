import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";
import { debounce } from "lodash";

import { Link } from "react-router-dom";
import { useSearchParams } from "react-router-dom-v5-compat";
import PaginationFooter from "../PaginationFooter/PaginationFooter";

const Groups = (props) => {
  var groups_data = useSelector((state) => state.groups_data),
    groups_page = useSelector((state) => state.groups_page),
    dispatch = useDispatch();

  let [searchParams, setSearchParams] = useSearchParams();

  var offset = parseInt(searchParams.get("offset", "0")) || 0;
  var limit = parseInt(searchParams.get("limit", "0")) || window.api_page_limit;

  const setOffset = (offset) => {
    console.log("setting offset", offset);
    if (offset < 0) {
      offset = 0;
    }
    setSearchParams((params) => {
      params.set("offset", offset);
      return params;
    });
    dispatch({
      type: "GROUPS_OFFSET",
      value: {
        offset: offset,
      },
    });
  };

  const setLimit = (newLimit) => {
    if (newLimit < 1) {
      newLimit = 10;
    }
    setSearchParams((params) => {
      params.set("limit", newLimit);
      return params;
    });
    dispatch({
      type: "GROUP_LIMIT",
      value: {
        limit: newLimit,
      },
    });
  };

  var total = groups_page ? groups_page.total : undefined;

  var { updateGroups, history } = props;

  const dispatchPageUpdate = (data, page) => {
    dispatch({
      type: "GROUPS_PAGE",
      value: {
        data: data,
        page: page,
      },
    });
  };

  useEffect(() => {
    updateGroups(offset, limit).then((data) =>
      dispatchPageUpdate(data.items, data._pagination),
    );
  }, [offset, limit]);

  if (!groups_data || !groups_page) {
    return <div data-testid="no-show"></div>;
  }

  const handleLimit = debounce(async (event) => {
    setLimit(event.target.value);
  }, 300);

  return (
    <div className="container" data-testid="container">
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
                offset={offset}
                limit={limit}
                visible={groups_data.length}
                total={total}
                next={() => setOffset(offset + limit)}
                prev={() => setOffset(offset - limit)}
                handleLimit={handleLimit}
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
