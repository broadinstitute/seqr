import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Table } from 'semantic-ui-react'

const StyledSortableTable = styled(Table)`
  &.ui.basic.sortable.table thead th {
    background: transparent;
    border-left: none;
    overflow: initial;
  }
`

const compareObjects = field => (a, b) => {
  let valA = a[field]
  let valB = b[field]
  if (typeof valA === 'string') { valA = valA.toLowerCase() }
  if (typeof valB === 'string') { valB = valB.toLowerCase() }

  if (valA < valB) {
    return -1
  }
  else if (valA > valB) {
    return 1
  }
  return 0
}

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
      sortedData: props.defaultSortColumn ? props.data.sort(compareObjects(props.defaultSortColumn)) : props.data,
      column: props.defaultSortColumn,
      direction: 'ascending',
    }
  }

  handleSort = clickedColumn => () => {
    const { column, direction, sortedData } = this.state

    if (column !== clickedColumn) {
      this.setState({
        column: clickedColumn,
        sortedData: sortedData.sort(compareObjects(clickedColumn)),
        direction: 'ascending',
      })
    } else {
      this.setState({
        sortedData: sortedData.reverse(),
        direction: direction === 'ascending' ? 'descending' : 'ascending',
      })
    }
  }

  render() {
    const { data, defaultSortColumn, idField, columns, ...tableProps } = this.props
    const { column, direction, sortedData } = this.state

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
