import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import { Button, Card } from "react-bootstrap";
import { Link, useNavigate } from "react-router";
import { usePaginationParams } from "../../util/paginationParams";
import PaginationFooter from "../PaginationFooter/PaginationFooter";
import { MainContainer } from "../../util/layout";

const Groups = (props) => {
  const groups_data = useSelector((state) => state.groups_data);
  const groups_page = useSelector((state) => state.groups_page);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const { offset, setOffset, handleLimit, limit } = usePaginationParams();

  const total = groups_page ? groups_page.total : undefined;

  const { updateGroups } = props;

  const dispatchPageUpdate = (data, page) => {
    dispatch({
      type: "GROUPS_PAGE",
      value: {
        data: data,
        page: page,
      },
    });
  };

  // single callback to reload the page
  // uses current state
  const loadPageData = (params) => {
    const abortHandle = { cancelled: false };
    (async () => {
      try {
        const data = await updateGroups(offset, limit);
        // cancelled (e.g. param changed while waiting for response)
        if (abortHandle.cancelled) return;
        if (
          data._pagination.offset &&
          data._pagination.total <= data._pagination.offset
        ) {
          // reset offset if we're out of bounds,
          // then load again
          setOffset(0);
          return;
        }
        // actually update page data
        dispatchPageUpdate(data.items, data._pagination);
      } catch (e) {
        console.error("Failed to update group list.", e);
      }
    })();
    // returns cancellation callback
    return () => {
      // cancel stale load
      abortHandle.cancelled = true;
    };
  };

  useEffect(() => {
    return loadPageData();
  }, [limit, offset]);

  if (!groups_data || !groups_page) {
    return <div data-testid="no-show"></div>;
  }

  return (
    <MainContainer>
      <Card>
        <Card.Header>
          <h4>Groups</h4>
        </Card.Header>
        <Card.Body>
          <ul className="list-group">
            {groups_data.length > 0 ? (
              groups_data.map((e, i) => (
                <li className="list-group-item" key={"group-item" + i}>
                  <span className="badge rounded-pill bg-success mx-2">
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
            offset={groups_page.offset}
            limit={limit}
            visible={groups_data.length}
            total={total}
            next={() => setOffset(groups_page.offset + limit)}
            prev={() =>
              setOffset(
                limit > groups_page.offset ? 0 : groups_page.offset - limit,
              )
            }
            handleLimit={handleLimit}
          />
        </Card.Body>
        <Card.Footer>
          <Link to="/">
            <Button variant="light" id="return">
              Back
            </Button>
          </Link>
          <span> </span>
          <Link to="/create-group">
            <Button variant="primary">New Group</Button>
          </Link>
        </Card.Footer>
      </Card>
    </MainContainer>
  );
};

Groups.propTypes = {
  updateUsers: PropTypes.func,
  updateGroups: PropTypes.func,
};

export default Groups;
