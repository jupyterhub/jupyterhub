import React from "react";
import { withProps } from "recompose";
import { Col, Row, Container } from "react-bootstrap";
import PropTypes from "prop-types";
import ErrorAlert from "./error";

export const MainCol = (props) => {
  // main column layout
  // sets default width, span
  return withProps({
    md: { span: 10, offset: 1 },
    lg: { span: 8, offset: 2 },
    ...props,
  })(Col)();
};

export const MainContainer = (props) => {
  // default container for an admin page
  // adds errorAlert and sets main column width
  props = props || {};
  return (
    <Container data-testid="container">
      <ErrorAlert
        errorAlert={props.errorAlert}
        setErrorAlert={props.setErrorAlert}
      />
      <Row>
        <MainCol>{props.children}</MainCol>
      </Row>
    </Container>
  );
};

MainContainer.propTypes = {
  errorAlert: PropTypes.string,
  setErrorAlert: PropTypes.func,
  children: PropTypes.node,
};
