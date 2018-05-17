import React from 'react'
import PropTypes from 'prop-types'

import { Popup, Table } from 'semantic-ui-react'
//import randomMC from 'random-material-color'

import ColoredIcon from '../icons/ColoredIcon'

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
                dataWithPercents.map(d => (d.percent >= 1 ?
                  <div key={d.name} style={{
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
              <Table basic="very" compact="very">
                <Table.Body>
                  {
                    dataWithPercents.map(d => (
                      d.count > 0 ?
                        <Table.Row key={d.name} verticalAlign="top" >
                          <Table.Cell collapsing><ColoredIcon name="square" size="small" color={d.color} /> {d.count}</Table.Cell>
                          <Table.Cell singleLine>{d.name}</Table.Cell>
                          <Table.Cell collapsing>({d.percent}%)</Table.Cell>
                        </Table.Row> : null
                    ))
                  }

                  {
                    dataWithPercents.filter(d => d.count > 0).length > 1 ?
                      <Table.Row>
                        <Table.Cell><ColoredIcon name="square" size="small" color="white" /> {total}</Table.Cell>
                        <Table.Cell>Total</Table.Cell>
                        <Table.Cell />
                      </Table.Row> : null
                  }
                </Table.Body>
              </Table>
            </div>
          }
          position="right center"
          size="small"
        />
      </div>)
  }
}

export default HorizontalStackedBar

