export const jhapiRequest = (endpoint, method, data) => {
  let base_url = window.base_url || "/",
    api_url = `${base_url}hub/api`;
  return fetch(api_url + endpoint, {
    method: method,
    json: true,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/jupyterhub-pagination+json",
    },
    body: data ? JSON.stringify(data) : null,
  });
};
