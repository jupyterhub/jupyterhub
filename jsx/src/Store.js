import { combineReducers } from "redux";

export const initialState = {
  user_data: undefined,
  user_page: 0,
  groups_data: undefined,
  groups_page: 0,
  limit: 50,
  manage_groups_modal: false,
};

export const reducers = (state = initialState, action) => {
  switch (action.type) {
    case "USER_DATA":
      return Object.assign({}, state, { user_data: action.value });
    case "USER_PAGE":
      return Object.assign({}, state, {
        user_page: action.value.page,
        user_data: action.value.data,
      });
    case "GROUPS_DATA":
      return Object.assign({}, state, { groups_data: action.value });
    case "TOGGLE_MANAGE_GROUPS_MODAL":
      return Object.assign({}, state, {
        manage_groups_modal: !state.manage_groups_modal,
      });
    default:
      return state;
  }
};
