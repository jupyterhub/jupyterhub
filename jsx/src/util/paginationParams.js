import { debounce } from "lodash";
import { useSearchParams } from "react-router-dom";

export const usePaginationParams = () => {
  // get offset, limit, name filter from URL
  const [searchParams, setSearchParams] = useSearchParams();
  const offset = parseInt(searchParams.get("offset", "0")) || 0;
  const limit =
    parseInt(searchParams.get("limit", "0")) || window.api_page_limit || 100;

  const _setOffset = (params, offset) => {
    if (offset < 0) offset = 0;
    if (offset === 0) {
      params.delete("offset");
    } else {
      params.set("offset", offset);
    }
  };
  const _setLimit = (params, limit) => {
    if (limit < 1) limit = 1;
    if (limit === window.api_page_limit) {
      params.delete("limit");
    } else {
      params.set("limit", limit);
    }
  };
  const setPagination = (pagination) => {
    // update pagination in one
    if (!pagination) {
      return;
    }
    setSearchParams((params) => {
      _setOffset(params, pagination.offset);
      _setLimit(params, pagination.limit);
      return params;
    });
  };

  const setOffset = (offset) => {
    if (offset < 0) offset = 0;
    setSearchParams((params) => {
      _setOffset(params, offset);
      return params;
    });
  };

  const setLimit = (limit) => {
    setSearchParams((params) => {
      _setLimit(params, limit);
      return params;
    });
  };

  const handleLimit = debounce(async (event) => {
    setLimit(event.target.value);
  }, 300);

  return {
    offset,
    setOffset,
    limit,
    setLimit,
    handleLimit,
    setPagination,
  };
};
