import React from 'react'
import PropTypes from 'prop-types'

import { Icon, Popup } from 'semantic-ui-react'
import { Link } from 'react-router-dom'
//import randomMC from 'random-material-color'

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
    const { title, data, width, height, linkPath, showAllPopupCategories, minPercent = 1, noDataMessage = null } = this.props
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
                <table>
                  <tbody>
                    {
                      popupData.map(d => (
                        <tr key={d.name} style={{ whitespace: 'nowrap' }}>
                          {!d.header &&
                            <td style={{ paddingRight: '5px', width: '55px', verticalAlign: 'top' }}>
                              <Icon name="square" size="small" style={{ color: d.color }} /> {d.count}
                            </td>
                          }
                          <td colSpan={d.header ? 3 : 1} style={{ whitespace: 'nowrap', color: d.header ? 'grey' : 'inherit' }}>
                            {d.name}
                          </td>
                          {!d.header &&
                            <td style={{ paddingLeft: '5px', width: '50px', verticalAlign: 'top' }}>
                              ({Math.trunc(d.percent)}%)
                            </td>
                          }
                        </tr>
                      ))
                    }
                    <tr>
                      <td><Icon name="square" size="small" style={{ color: 'white' }} /> {total}</td>
                      <td>Total</td>
                      <td />
                    </tr>
                  </tbody>
                </table>
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

