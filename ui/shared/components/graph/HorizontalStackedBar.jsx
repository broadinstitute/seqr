import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { Popup, Table } from 'semantic-ui-react'
import { Link } from 'react-router-dom'
//import randomMC from 'random-material-color'

import { ColoredIcon, NoBorderTable } from '../StyledComponents'


const BarContainer = styled.div.attrs({
  w: (props) => { return props.width ? `${props.width}${typeof props.width === 'number' ? 'px' : ''}` : '100%' },
  h: (props) => { return props.height ? `${props.height}px` : 'auto' },
  lh: (props) => { return props.height ? `${props.height - 2}px` : 'inherit' },
})`
  display: inline-block;
  width: ${props => props.w};
  height: ${props => props.h};
  line-height: ${props => props.lh};
  text-align: center;
  border: 1px solid gray;`

const BarSection = styled(({ to, ...props }) => React.createElement(to ? Link : 'div', { to, ...props }))`  
  display: inline-block;
  height: 100%;
  width: ${props => props.percent}%;
  background-color: ${props => props.color};`

const NoWrap = styled.span`
  white-space: nowrap;`

const TableRow = styled(Table.Row)`
  padding: 0px !important;`

const TableCell = styled(Table.Cell)`
  padding: .2em .6em !important;`


class HorizontalStackedBar extends React.PureComponent {

  static propTypes = {
    title: PropTypes.string.isRequired,
    data: PropTypes.arrayOf(PropTypes.object), //an array of objects with keys: name, count, color, percent
    width: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    height: PropTypes.number,
    linkPath: PropTypes.string,
    minPercent: PropTypes.number,
    noDataMessage: PropTypes.string,
    showAllPopupCategories: PropTypes.bool,
    showPercent: PropTypes.bool,
    showTotal: PropTypes.bool,
    sectionLinks: PropTypes.bool,
  }

  render() {
    const {
      title, data, width, height, linkPath, sectionLinks, showAllPopupCategories, minPercent = 1,
      noDataMessage = 'No Data', showPercent = true, showTotal = true,
    } = this.props
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
                <BarSection key={d.name} to={(sectionLinks && linkPath) ? `${linkPath}/${d.name}` : linkPath} color={d.color} percent={d.percent} />,
              )}
            </NoWrap>
          }
          content={
            <div>
              {title && <div><b>{title}</b><br /></div>}
              <NoBorderTable basic="very" compact="very">
                <Table.Body>
                  {
                    popupData.map(d => (
                      <TableRow key={d.name} verticalAlign="top" >
                        {!d.header &&
                          <TableCell collapsing textAlign="right">{d.count} <ColoredIcon name="square" size="small" color={d.color} /></TableCell>
                        }
                        <TableCell singleLine colSpan={d.header ? 3 : 1} disabled={Boolean(d.header)}>{d.name}</TableCell>
                        {!d.header && <TableCell collapsing>{showPercent && `(${d.percent.toPrecision(2)}%)`}</TableCell>}
                      </TableRow>
                    ))
                  }
                  {showTotal &&
                    <TableRow>
                      <TableCell textAlign="right"><b>{total}</b></TableCell>
                      <TableCell><b>Total</b></TableCell>
                      <TableCell />
                    </TableRow>
                  }
                </Table.Body>
              </NoBorderTable>
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

