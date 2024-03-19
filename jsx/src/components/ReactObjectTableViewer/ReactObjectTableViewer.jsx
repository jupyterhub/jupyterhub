// Originally copied from
// https://github.com/jinkwon/react-object-table-viewer/blob/f29827028fad547a0a17e044567cf1486849fb7a/src/ReactObjectTableViewer.tsx
import React from "react";
import PropTypes from "prop-types";

const ReactObjectTableViewer = (props) => {
  const opt = props;

  const data = opt.data;
  const keys = Object.keys(data || {}) || [];

  return (
    <table
      className={opt.className}
      style={{
        ...opt.style,
      }}
    >
      <tbody>
        {keys.map((k, key) => {
          const val = data[k];
          const isObject = typeof val === "object";
          const isElement = React.isValidElement(val);

          return (
            <tr key={key}>
              <th
                style={{
                  ...opt.keyStyle,
                }}
              >
                {k}
              </th>
              {isObject && (
                <td>
                  {isElement && val}
                  {!isElement && <ReactObjectTableViewer {...opt} data={val} />}
                </td>
              )}
              {!isObject && (
                <td
                  style={{
                    whiteSpace: "nowrap",
                    ...opt.valueStyle,
                  }}
                >{`${val}`}</td>
              )}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
};

ReactObjectTableViewer.propTypes = {
  data: PropTypes.object,
  style: PropTypes.objectOf(PropTypes.string),
  keyStyle: PropTypes.objectOf(PropTypes.string),
  valueStyle: PropTypes.objectOf(PropTypes.string),
  className: PropTypes.string,
  layout: PropTypes.string,
};

export default ReactObjectTableViewer;
