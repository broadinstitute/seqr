/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'

import { Icon, Popup } from 'semantic-ui-react'
//import randomMC from 'random-material-color'

class HorizontalStackedBar extends React.Component {

  static propTypes = {
    title: PropTypes.string.isRequired,
    data: PropTypes.arrayOf(PropTypes.object), //an array of objects with keys: name, count, color, percent
    width: PropTypes.number,
    height: PropTypes.number,
  }

  render() {
    const { title, data, width, height } = this.props
    const total = data.reduce((acc, d) => acc + d.count, 0)
    const dataWithPercents = data.reduce(
      (acc, d) => [
        ...acc,
        {
          ...d,
          percent: Math.trunc((100 * (d.count || 0)) / total),
        },
      ],
      [],
    )
    //const colors = data.map(d => d.color) || Array(data.length).map(() => randomMC.getColor())

    return (
      <div style={{
        display: 'inline-block',
        ...(width ? { width: `${width}px` } : {}),
        ...(height ? { height: `${height}px` } : {}),
        ...(total === 0 ? { border: '1px solid gray' } : {}),
      }}
      >
        <Popup
          trigger={
            <span style={{ whiteSpace: 'nowrap' }}>
              {
                dataWithPercents.map((d, i) => (d.percent >= 1 ?
                  <div key={i} style={{
                    height: '100%',
                    width: `${d.percent}%`,
                    backgroundColor: d.color,
                    display: 'inline-block',
                  }}
                  /> : null
                ))
              }
            </span>
          }
          content={
            <div>
              {title && <div><b>{title}</b><br /></div>}
              <table>
                <tbody>
                  {
                    dataWithPercents.map((d, i) => (
                      d.count > 0 ?
                        <tr key={i} style={{ whitespace: 'nowrap' }}>
                          <td style={{ paddingRight: '5px', width: '55px', verticalAlign: 'top' }}><Icon name="square" size="small" style={{ color: d.color }} /> {d.count}</td>
                          <td style={{ whitespace: 'nowrap' }}>{d.name}</td>
                          <td style={{ paddingLeft: '5px', width: '50px', verticalAlign: 'top' }}>({d.percent}%)</td>
                        </tr> : null
                    ))
                  }

                  {
                    dataWithPercents.filter(d => d.count > 0).length > 1 ?
                      <tr>
                        <td><Icon name="square" size="small" style={{ color: 'white' }} /> {total}</td>
                        <td>Total</td>
                        <td />
                      </tr> : null
                  }
                </tbody>
              </table>
            </div>
          }
          position="right center"
          size="small"
        />
      </div>)
  }
}

export default HorizontalStackedBar

