import React from "react";
import PropTypes from "prop-types";
import { Button, FormControl } from "react-bootstrap";

import "./pagination-footer.css";

const PaginationFooter = (props) => {
  const { offset, limit, visible, total, next, prev, handleLimit } = props;
  return (
    <div className="pagination-footer">
      <p>
        Displaying {visible ? offset + 1 : offset}-{offset + visible}{" "}
        {total ? `of ${total}` : ""}
        <br />
        {offset >= 1 ? (
          <Button variant="light" size="sm">
            <span
              className="active-pagination"
              data-testid="paginate-prev"
              onClick={prev}
            >
              Previous
            </span>
          </Button>
        ) : (
          <Button variant="light" size="sm">
            <span className="inactive-pagination">Previous</span>
          </Button>
        )}
        {offset + visible < total ? (
          <Button variant="light" size="sm">
            <span
              className="active-pagination"
              data-testid="paginate-next"
              onClick={next}
            >
              Next
            </span>
          </Button>
        ) : (
          <Button variant="light" size="sm">
            <span className="inactive-pagination">Next</span>
          </Button>
        )}
        <label>
          Items per page:
          <FormControl
            type="number"
            min="25"
            step="25"
            name="pagination-limit"
            placeholder={limit}
            aria-label="pagination-limit"
            defaultValue={limit}
            onChange={handleLimit}
          />
        </label>
      </p>
    </div>
  );
};

PaginationFooter.propTypes = {
  endpoint: PropTypes.string,
  offset: PropTypes.number,
  limit: PropTypes.number,
  visible: PropTypes.number,
  total: PropTypes.number,
  handleLimit: PropTypes.func,
  next: PropTypes.func,
  prev: PropTypes.func,
};

export default PaginationFooter;
