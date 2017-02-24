/* eslint-disable */

import React from 'react'
import { Icon, Popup } from 'semantic-ui-react'
import randomMC from 'random-material-color'

class HorizontalStackedBar extends React.Component {

  static propTypes = {
    title: React.PropTypes.string,
    counts: React.PropTypes.object,
    names: React.PropTypes.arrayOf(React.PropTypes.string),
    colors: React.PropTypes.arrayOf(React.PropTypes.string),
    width: React.PropTypes.number,
    height: React.PropTypes.number,
  }

  render() {
    const { title, counts, names, width, height }  = this.props

    const total = Object.values(counts).reduce((a, b) => a+b, 0)
    if (total === 0 || width === 0) {
      return null
    }

    const colors = this.props.colors || Array(names.length).map(() => randomMC.getColor())
    const percents = names.map(n => Math.trunc((100 * (counts[n] || 0)) / total))

    return <div style={{
      display: 'inline-block',
      ...(width ? {width: `${width}px`} : {}),
      ...(height ? {height: `${height}px`} : {})}}
    >
      <Popup
        trigger={
          <span style={{ whiteSpace: 'nowrap' }}>{
            names.map((n, i) => percents[i] >= 1 ?
              <div key={i} style={{
                height: '100%',
                width: `${percents[i]}%`,
                backgroundColor: colors[i],
                display: 'inline-block',
              }}
              /> : null
            )
          }</span>
        }
        content={<div>
          {title && <div><b>{title}</b><br /></div>}
          <table>
            <tbody>
            {
              names.map((n, i) => (
                counts[n] > 0 ?
                <tr key={names[i]}>
                  <td style={{ paddingRight: '5px', width: '55px', verticalAlign: 'top' }}><Icon name="square" size="small" style={{ color: colors[i] }} /> {counts[n]}</td>
                  <td>{names[i]}</td>
                  <td style={{ paddingLeft: '5px', width: '50px', verticalAlign: 'top' }}>({percents[i]}%)</td>
                </tr> : null ))
            }
            {
              names.filter(n => counts[n] > 0).length > 1 ?
                <tr>
                  <td><Icon name="square" size="small" style={{ color: 'white' }} /> {total}</td>
                  <td>Total</td>
                  <td></td>
                </tr> : null
            }
          </tbody></table>
        </div>}
        positioning="right center"
        size="small"
      />
    </div>
  }
}


export default HorizontalStackedBar

