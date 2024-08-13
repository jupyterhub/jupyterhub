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
