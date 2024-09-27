import React from "react";
import { Button, Alert, Col, Row } from "react-bootstrap";
import PropTypes from "prop-types";

const ErrorAlert = (props) => {
  const { errorAlert, setErrorAlert } = props;
  if (!errorAlert) {
    return <></>;
  }
  return (
    <Row>
      <Col md={{ span: 10, offset: 1 }} lg={{ span: 8, offset: 2 }}>
        <Alert variant="danger">
          {errorAlert}
          <Button
            variant="close"
            className="float-end"
            aria-label="Close"
            onClick={() => setErrorAlert(null)}
          ></Button>
        </Alert>
      </Col>
    </Row>
  );
};

ErrorAlert.propTypes = {
  errorAlert: PropTypes.string,
  setErrorAlert: PropTypes.func,
};

export default ErrorAlert;
