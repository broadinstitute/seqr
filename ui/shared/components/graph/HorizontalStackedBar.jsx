import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { Popup, Table } from 'semantic-ui-react'
import { Link } from 'react-router-dom'
//import randomMC from 'random-material-color'

import { ColoredIcon } from '../StyledComponents'


const BarContainer = styled.div`
  display: inline-block;
  width: ${(props) => { return props.width ? `${props.width}px` : '100%' }};
  height: ${(props) => { return props.height ? `${props.height}px` : 'auto' }};
  line-height: ${(props) => { return props.height ? `${props.height - 2}px` : 'inherit' }};
  text-align: center;
  border: 1px solid gray;`

const BarSection = styled(({ to, ...props }) => React.createElement(to ? Link : 'div', { to, ...props }))`  
  display: inline-block;
  height: 100%;
  width: ${props => props.percent}%;
  background-color: ${props => props.color};`

const NoWrap = styled.span`
  white-space: nowrap;`

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

    if (total === 0) {
      return <BarContainer width={width} height={height}>{noDataMessage}</BarContainer>
    }

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
      <BarContainer width={width} height={height}>
        <Popup
          trigger={
            <NoWrap>
              {dataWithPercents.filter(d => d.percent >= minPercent).map(d =>
                <BarSection key={d.name} to={linkPath && `${linkPath}/${d.name}`} color={d.color} percent={d.percent} />,
              )}
            </NoWrap>
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
                        {!d.header && <Table.Cell collapsing>({d.percent.toPrecision(2)}%)</Table.Cell>}
                      </Table.Row>
                    ))
                  }
                  <Table.Row>
                    <Table.Cell><ColoredIcon name="square" size="small" color="white" /> {total}</Table.Cell>
                    <Table.Cell>Total</Table.Cell>
                    <Table.Cell />
                  </Table.Row>
                </Table.Body>
              </Table>
            </div>
          }
          position="bottom center"
          size="small"
          hoverable
          flowing
        />
      </BarContainer>)
  }
}

export default HorizontalStackedBar

