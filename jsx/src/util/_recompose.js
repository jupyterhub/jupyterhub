// extracted tiny subset we use from react-recompose
// we probably don't need these at all,
// but vendor before refactoring

// https://github.com/acdlite/recompose
// License: MIT
// Copyright (c) 2015-2018 Andrew Clark

import { createElement } from "react";

function createFactory(type) {
  return createElement.bind(null, type);
}

export const compose = (...funcs) =>
  funcs.reduce(
    (a, b) =>
      (...args) =>
        a(b(...args)),
    (arg) => arg,
  );

const mapProps = (propsMapper) => (BaseComponent) => {
  const factory = createFactory(BaseComponent);
  const MapProps = (props) => factory(propsMapper(props));
  return MapProps;
};

export const withProps = (input) => {
  const hoc = mapProps((props) => ({
    ...props,
    ...(typeof input === "function" ? input(props) : input),
  }));
  return hoc;
};
