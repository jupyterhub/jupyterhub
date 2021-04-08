import React, { useState } from "react";
import "./multi-select.css";
import PropTypes from "prop-types";

const Multiselect = (props) => {
  var { onChange, options, value } = props;

  var [selected, setSelected] = useState(value);

  if (!options) return null;

  return (
    <div className="multi-container">
      <div>
        {selected.map((e, i) => (
          <div
            key={"selected" + i}
            className="item selected"
            onClick={() => {
              let updated_selection = selected
                .slice(0, i)
                .concat(selected.slice(i + 1));
              onChange(updated_selection, options);
              setSelected(updated_selection);
            }}
          >
            {e}
          </div>
        ))}
        {options.map((e, i) =>
          selected.includes(e) ? undefined : (
            <div
              key={"unselected" + i}
              className="item unselected"
              onClick={() => {
                let updated_selection = selected.concat([e]);
                onChange(updated_selection, options);
                setSelected(updated_selection);
              }}
            >
              {e}
            </div>
          )
        )}
      </div>
    </div>
  );
};

Multiselect.propTypes = {
  value: PropTypes.array,
  onChange: PropTypes.func,
  options: PropTypes.array,
};

export default Multiselect;
