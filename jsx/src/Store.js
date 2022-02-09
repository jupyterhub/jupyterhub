export const initialState = {
  user_data: undefined,
  user_page: 0,
  groups_data: undefined,
  groups_page: 0,
  limit: window.api_page_limit,
};

export const reducers = (state = initialState, action) => {
  switch (action.type) {
    // Updates the client user model data and stores the page
    case "USER_PAGE":
      return Object.assign({}, state, {
        user_page: action.value.page,
        user_data: action.value.data,
      });

    // Updates the client group model data and stores the page
    case "GROUPS_PAGE":
      return Object.assign({}, state, {
        groups_page: action.value.page,
        groups_data: action.value.data,
      });

    default:
      return state;
  }
};
