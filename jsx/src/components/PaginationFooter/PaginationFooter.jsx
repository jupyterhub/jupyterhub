import React from "react";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

import "./pagination-footer.css";

const PaginationFooter = (props) => {
  let { endpoint, page, limit, numOffset, numElements } = props;
  return (
    <div className="pagination-footer">
      <p>
        Displaying {numOffset}-{numOffset + numElements}
        <br></br>
        <br></br>
        {page >= 1 ? (
          <button className="btn btn-sm btn-light spaced">
            <Link to={`${endpoint}?page=${page - 1}`}>
              <span className="active-pagination">Previous</span>
            </Link>
          </button>
        ) : (
          <button className="btn btn-sm btn-light spaced">
            <span className="inactive-pagination">Previous</span>
          </button>
        )}
        {numElements >= limit ? (
          <button className="btn btn-sm btn-light spaced">
            <Link to={`${endpoint}?page=${page + 1}`}>
              <span className="active-pagination">Next</span>
            </Link>
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
