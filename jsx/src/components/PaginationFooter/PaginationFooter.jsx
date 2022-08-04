import React from "react";
import PropTypes from "prop-types";

import "./pagination-footer.css";

const PaginationFooter = (props) => {
  let { offset, limit, visible, total, next, prev } = props;
  return (
    <div className="pagination-footer">
      <p>
        Displaying {offset}-{offset + visible}
        <br></br>
        <br></br>
        {offset >= 1 ? (
          <button className="btn btn-sm btn-light spaced">
            <span
              className="active-pagination"
              data-testid="paginate-prev"
              onClick={prev}
            >
              Previous
            </span>
          </button>
        ) : (
          <button className="btn btn-sm btn-light spaced">
            <span className="inactive-pagination">Previous</span>
          </button>
        )}
        {offset + visible < total ? (
          <button className="btn btn-sm btn-light spaced">
            <span
              className="active-pagination"
              data-testid="paginate-next"
              onClick={next}
            >
              Next
            </span>
          </button>
        ) : (
          <button className="btn btn-sm btn-light spaced">
            <span className="inactive-pagination">Next</span>
          </button>
        )}
      </p>
    </div>
  );
};

PaginationFooter.propTypes = {
  endpoint: PropTypes.string,
  page: PropTypes.number,
  limit: PropTypes.number,
  numOffset: PropTypes.number,
  numElements: PropTypes.number,
};

export default PaginationFooter;
