import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import { Link, useNavigate } from "react-router-dom";
import { usePaginationParams } from "../../util/paginationParams";
import PaginationFooter from "../PaginationFooter/PaginationFooter";

const Groups = (props) => {
  const groups_data = useSelector((state) => state.groups_data);
  const groups_page = useSelector((state) => state.groups_page);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const { setOffset, offset, handleLimit, limit, setPagination } =
    usePaginationParams();

  const total = groups_page ? groups_page.total : undefined;

  const { updateGroups } = props;

  const dispatchPageUpdate = (data, page) => {
    setPagination(page);
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
                      <Link to="/group-edit" state={{ group_data: e }}>
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
                  navigate("/create-group");
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
};

export default Groups;
