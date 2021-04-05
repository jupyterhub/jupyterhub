import React, { Component } from "react";
import "./multi-select.css";
import PropTypes from "prop-types";

export default class Multiselect extends Component {
  static get propTypes() {
    return {
      value: PropTypes.array,
      onChange: PropTypes.func,
      options: PropTypes.array,
    };
  }

  constructor(props) {
    super(props);
    this.state = {
      selected: props.value,
    };
  }

  render() {
    var { onChange, options, value } = this.props;

    if (!options) return null;

    return (
      <div className="multi-container">
        <div>
          {this.state.selected.map((e, i) => (
            <div
              key={"selected" + i}
              className="item selected"
              onClick={() => {
                let updated_selection = this.state.selected
                  .slice(0, i)
                  .concat(this.state.selected.slice(i + 1));
                onChange(updated_selection, options);
                this.setState(
                  Object.assign({}, this.state, { selected: updated_selection })
                );
              }}
            >
              {e}
            </div>
          ))}
          {options.map((e, i) =>
            this.state.selected.includes(e) ? undefined : (
              <div
                key={"unselected" + i}
                className="item unselected"
                onClick={() => {
                  let updated_selection = this.state.selected.concat([e]);
                  onChange(updated_selection, options);
                  this.setState(
                    Object.assign({}, this.state, {
                      selected: updated_selection,
                    })
                  );
                }}
              >
                {e}
              </div>
            )
          )}
        </div>
      </div>
    );
  }
}
