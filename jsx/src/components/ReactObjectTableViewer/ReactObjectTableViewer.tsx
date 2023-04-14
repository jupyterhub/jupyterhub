import React, {
  CSSProperties,
  FC
} from 'react';
import { TableViewerLayoutType } from './types';

export interface PropTypes {
  data?: Record<string, unknown>;
  style?: CSSProperties;
  keyStyle?: CSSProperties;
  valueStyle?: CSSProperties;
  className?: string;
  layout?: TableViewerLayoutType;
}

const ReactObjectTableViewer: FC<PropTypes> = (props: PropTypes) => {
  const opt = {
    layout: 'vertical' as TableViewerLayoutType,
    ...props,
  };

  const data: any = opt.data;
  const keys: string[] = Object.keys(data || {}) || [];

  return (
    <table
      className={opt.className}
      style={{
        ...opt.style,
      }}
    >
      {opt.layout === 'vertical' && (
        <tbody>
        {keys.map((k, key) => {
          const val: any = data[k];
          const isObject: boolean = typeof val === 'object';

          return <tr key={key}>
            <th
              style={{
                ...opt.keyStyle,
              }}
            >{k}</th>
            {isObject && <td><ReactObjectTableViewer {...opt} data={val}/></td>}
            {!isObject && <td
              style={{
                whiteSpace: 'nowrap',
                ...opt.valueStyle,
              }}
            >{`${val}`}</td>}
          </tr>;
        })}
        </tbody>
      )}

      {opt.layout === 'horizontal' && (
        <tbody>
          <tr>
          {keys.map((k, key) => (<th
            key={key}
            style={{
              ...opt.keyStyle,
            }}
          >{k}</th>))}
          </tr>
          <tr>
          {keys.map((k, key) => {
            const val: any = data[k];
            const isObject: boolean = typeof val === 'object';

            return <React.Fragment key={key}>
              {isObject && <td><ReactObjectTableViewer {...opt} data={val}/></td>}
              {!isObject && <td
                key={key}
                style={{
                  whiteSpace: 'nowrap',
                  ...opt.valueStyle,
                }}
              >{`${val}`}</td>}
            </React.Fragment>;
          })}
          </tr>
        </tbody>
      )}
    </table>
  );
};

export default ReactObjectTableViewer;
