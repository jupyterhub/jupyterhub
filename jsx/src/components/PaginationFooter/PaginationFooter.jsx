import React from "react";
import PropTypes from "prop-types";
import { Button, FormControl } from "react-bootstrap";

const PaginationFooter = (props) => {
  const { offset, limit, visible, total, next, prev, handleLimit } = props;
  return (
    <div className="pagination-footer">
      <p>
        Displaying {visible ? offset + 1 : offset}-{offset + visible}{" "}
        {total ? `of ${total}` : ""}
        <br />
        {offset >= 1 ? (
          <Button
            variant="light"
            size="sm"
            onClick={prev}
            className="me-2"
            data-testid="paginate-prev"
          >
            Previous
          </Button>
        ) : (
          <Button
            variant="light"
            size="sm"
            className="me-2"
            disabled
            aria-disabled="true"
          >
            Previous
          </Button>
        )}
        {offset + visible < total ? (
          <Button
            variant="light"
            size="sm"
            className="me-2"
            onClick={next}
            data-testid="paginate-next"
          >
            Next
          </Button>
        ) : (
          <Button
            variant="light"
            size="sm"
            className="me-2"
            disabled
            aria-disabled="true"
          >
            Next
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
