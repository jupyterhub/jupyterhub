const jhdata = window.jhdata || {};
const base_url = jhdata.base_url || "/";
const xsrfToken = jhdata.xsrf_token;

export const jhapiRequest = (endpoint, method, data) => {
  let api_url = `${base_url}hub/api`;
  let suffix = "";
  if (xsrfToken) {
    // add xsrf token to url parameter
    var sep = endpoint.indexOf("?") === -1 ? "?" : "&";
    suffix = sep + "_xsrf=" + xsrfToken;
  }
  return fetch(api_url + endpoint + suffix, {
    method: method,
    json: true,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/jupyterhub-pagination+json",
    },
    body: data ? JSON.stringify(data) : null,
  });
};
