export const jhapiRequest = (endpoint, method, data) => {
  return fetch("/hub/api" + endpoint, {
    method: method,
    json: true,
    headers: {
      "Content-Type": "application/json",
    },
    body: data ? JSON.stringify(data) : null,
  });
};
