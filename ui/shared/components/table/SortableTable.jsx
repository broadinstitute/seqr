import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Table } from 'semantic-ui-react'

import { compareObjects } from '../../utils/sortUtils'

const StyledSortableTable = styled(Table)`
  &.ui.basic.sortable.table thead th {
    background: transparent;
    border-left: none;
    overflow: initial;
  }
`
const ASCENDING = 'ascending'
const DESCENDING = 'descending'

class SortableTable extends React.PureComponent {

  static propTypes = {
    data: PropTypes.array,
    columns: PropTypes.array,
    idField: PropTypes.string,
    defaultSortColumn: PropTypes.string,
  }

  constructor(props) {
    super(props)

    this.state = {
      column: props.defaultSortColumn,
      direction: 'ascending',
    }
  }

  handleSort = clickedColumn => () => {
    const { column, direction } = this.state

    if (column !== clickedColumn) {
      this.setState({
        column: clickedColumn,
        direction: ASCENDING,
      })
    } else {
      this.setState({
        direction: direction === ASCENDING ? DESCENDING : ASCENDING,
      })
    }
  }

  render() {
    const { data, defaultSortColumn, idField, columns, ...tableProps } = this.props
    const { column, direction } = this.state

    let sortedData = data.sort(compareObjects(column))
    if (direction === DESCENDING) {
      sortedData = sortedData.reverse()
    }

    return (
      <StyledSortableTable sortable {...tableProps}>
        <Table.Header>
          <Table.Row>
            {columns.map(({ name, format, ...columnProps }) =>
              <Table.HeaderCell
                key={name}
                sorted={column === name ? direction : null}
                onClick={this.handleSort(name)}
                {...columnProps}
              />,
            )}
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {sortedData.map(row => (
            <Table.Row key={row[idField]}>
              {columns.map(({ name, format }) =>
                <Table.Cell
                  key={name}
                  content={format ? format(row) : row[name]}
                />,
              )}
            </Table.Row>
          ))}
        </Table.Body>
      </StyledSortableTable>
    )
  }
}

export default SortableTable
