import React from 'react'
import PropTypes from 'prop-types'

import { Popup, Table } from 'semantic-ui-react'
import { Link } from 'react-router-dom'
//import randomMC from 'random-material-color'

import { ColoredIcon } from '../StyledComponents'

class HorizontalStackedBar extends React.Component {

  static propTypes = {
    title: PropTypes.string.isRequired,
    data: PropTypes.arrayOf(PropTypes.object), //an array of objects with keys: name, count, color, percent
    width: PropTypes.number,
    height: PropTypes.number,
    linkPath: PropTypes.string,
    minPercent: PropTypes.number,
    noDataMessage: PropTypes.string,
    showAllPopupCategories: PropTypes.bool,
  }

  render() {
    const { title, data, width, height, linkPath, showAllPopupCategories, minPercent = 1, noDataMessage = 'No Data' } = this.props
    const total = data.reduce((acc, d) => acc + d.count, 0)
    const dataWithPercents = data.reduce(
      (acc, d) => [
        ...acc,
        {
          ...d,
          percent: (100 * (d.count || 0)) / total,
        },
      ],
      [],
    )
    //const colors = data.map(d => d.color) || Array(data.length).map(() => randomMC.getColor())
    let currCategory = null
    const popupData = dataWithPercents.reduce((acc, d) => {
      if (d.count <= 0 && !showAllPopupCategories) {
        return acc
      }
      if (d.category !== currCategory) {
        currCategory = d.category
        if (d.category) {
          acc.push({ name: d.category, header: true })
        }
      }
      acc.push(d)
      return acc
    }, [])

    return (
      <div style={{
        display: 'inline-block',
        ...{ width: width ? `${width}px` : '100%' },
        ...(height ? { height: `${height}px` } : {}),
      }}
      >
        {total > 0 ?
          <Popup
            trigger={
              <span style={{ whiteSpace: 'nowrap' }}>
                {dataWithPercents.filter(d => d.percent >= minPercent).map((d, i) => {
                  const barProps = {
                    key: i,
                    style: {
                      height: '100%',
                      width: `${d.percent}%`,
                      backgroundColor: d.color,
                      display: 'inline-block',
                    },
                  }
                  return linkPath ? <Link to={`${linkPath}/${d.name}`} {...barProps} /> : <div {...barProps} />
                })
                }
              </span>
            }
            content={
              <div>
                {title && <div><b>{title}</b><br /></div>}
                <Table basic="very" compact="very">
                  <Table.Body>
                    {
                      popupData.map(d => (
                        <Table.Row key={d.name} verticalAlign="top" >
                          {!d.header &&
                            <Table.Cell collapsing><ColoredIcon name="square" size="small" color={d.color} /> {d.count}</Table.Cell>
                          }
                          <Table.Cell singleLine colSpan={d.header ? 3 : 1} disabled={Boolean(d.header)}>{d.name}</Table.Cell>
                          {!d.header && <Table.Cell collapsing>({d.percent}%)</Table.Cell>}
                        </Table.Row>
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
            position="bottom center"
            size="small"
            hoverable
            flowing
          />
          :
          <div style={{ lineHeight: height ? `${height - 2}px` : 'inherit', textAlign: 'center', border: '1px solid gray' }}>
            {noDataMessage}
          </div>
        }
      </div>)
  }
}

export default HorizontalStackedBar

