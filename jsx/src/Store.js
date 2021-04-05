import { combineReducers } from "redux";

export const initialState = {
  user_data: undefined,
  groups_data: undefined,
  manage_groups_modal: false,
};

export const reducers = (state = initialState, action) => {
  switch (action.type) {
    case "USER_DATA":
      return Object.assign({}, state, { user_data: action.value });
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
