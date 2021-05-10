import { combineReducers } from "redux";

export const initialState = {
  user_data: undefined,
  user_page: 0,
  groups_data: undefined,
  groups_page: 0,
  limit: 50,
};

export const reducers = (state = initialState, action) => {
  switch (action.type) {
    // Updates the client user model data and stores the page
    case "USER_PAGE":
      return Object.assign({}, state, {
        user_page: action.value.page,
        user_data: action.value.data,
      });

    // Deprecated - doesn't store pagination values
    case "USER_DATA":
      return Object.assign({}, state, { user_data: action.value });

    // Updates the client group model data and stores the page
    case "GROUPS_PAGE":
      return Object.assign({}, state, {
        groups_page: action.value.page,
        groups_data: action.value.data,
      });

    // Deprecated - doesn't store pagination values
    case "GROUPS_DATA":
      return Object.assign({}, state, { groups_data: action.value });

    default:
      return state;
  }
};
