import PropTypes from "prop-types";

const jhdata = window.jhdata || {};
const base_url = jhdata.base_url || "/";
const xsrfToken = jhdata.xsrf_token;

export const jhapiRequest = (endpoint, method, data) => {
  let api_url = new URL(`${base_url}api` + endpoint, location.origin);
  if (xsrfToken) {
    api_url.searchParams.set("_xsrf", xsrfToken);
  }
  return fetch(api_url, {
    method: method,
    json: true,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/jupyterhub-pagination+json",
    },
    body: data ? JSON.stringify(data) : null,
  });
};

// need to declare the subset of fields we use, at least
export const Server = PropTypes.shape({
  name: PropTypes.string,
  url: PropTypes.string,
  active: PropTypes.boolean,
  pending: PropTypes.string,
  last_activity: PropTypes.string,
});

export const User = PropTypes.shape({
  admin: PropTypes.boolean,
  name: PropTypes.string,
  last_activity: PropTypes.string,
  url: PropTypes.string,
  server: Server,
  servers: PropTypes.objectOf(Server),
});
