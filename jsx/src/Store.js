export const initialState = {
  user_data: undefined,
  user_page: { offset: 0, limit: window.api_page_limit || 100 },
  name_filter: "",
  groups_data: undefined,
  groups_page: { offset: 0, limit: window.api_page_limit || 100 },
  limit: window.api_page_limit || 100,
};

export const reducers = (state = initialState, action) => {
  switch (action.type) {
    // Updates the client user model data and stores the page
    case "USER_OFFSET":
      return Object.assign({}, state, {
        user_page: Object.assign({}, state.user_page, {
          offset: action.value.offset,
        }),
      });

    case "USER_NAME_FILTER":
      // set offset to 0 if name filter changed,
      // otherwise leave it alone
      const newOffset =
        action.value.name_filter !== state.name_filter ? 0 : state.name_filter;
      return Object.assign({}, state, {
        user_page: Object.assign({}, state.user_page, {
          offset: newOffset,
        }),
        name_filter: action.value.name_filter,
      });

    case "USER_PAGE":
      return Object.assign({}, state, {
        user_page: action.value.page,
        user_data: action.value.data,
      });

    // Updates the client group user model data and stores the page
    case "GROUPS_OFFSET":
      return Object.assign({}, state, {
        groups_page: Object.assign({}, state.groups_page, {
          offset: action.value.offset,
        }),
      });

    case "GROUPS_PAGE":
      return Object.assign({}, state, {
        groups_page: action.value.page,
        groups_data: action.value.data,
      });

    default:
      return state;
  }
};
