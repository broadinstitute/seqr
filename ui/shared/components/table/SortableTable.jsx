import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Table, Checkbox } from 'semantic-ui-react'

import { compareObjects } from '../../utils/sortUtils'

const StyledSortableTable = styled(Table)`
  &.ui.basic.sortable.table thead th {
    background: transparent;
    border-left: none;
    overflow: initial;
  }
  
  &.ui.selectable tr:hover {
    cursor: pointer;
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
    selectRows: PropTypes.func,
  }

  constructor(props) {
    super(props)

    this.state = {
      column: props.defaultSortColumn,
      direction: 'ascending',
      selected: {},
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

  allSelected = () => (
    Object.keys(this.state.selected).length === this.props.data.length &&
    Object.values(this.state.selected).every(isSelected => isSelected)
  )
  someSelected = () => Object.values(this.state.selected).includes(true) && Object.values(this.state.selected).includes(false)

  selectAll = () => {
    if (!this.props.selectRows) {
      return
    }

    const rowIds = this.props.data.map(row => row[this.props.idField])
    const allSelected = !this.allSelected()
    this.props.selectRows(rowIds, allSelected)
    this.setState({ selected: rowIds.reduce((acc, rowId) => ({ ...acc, [rowId]: allSelected }), {}) })
  }

  handleSelect = rowId => () => {
    if (!this.props.selectRows) {
      return
    }

    const selected = !this.state.selected[rowId]
    this.props.selectRows([rowId], selected)
    this.setState({ selected: { ...this.state.selected, [rowId]: selected } })
  }

  render() {
    const { data, defaultSortColumn, idField, columns, selectRows, ...tableProps } = this.props
    const { column, direction, selected } = this.state

    let sortedData = data.sort(compareObjects(column))
    if (direction === DESCENDING) {
      sortedData = sortedData.reverse()
    }

    return (
      <StyledSortableTable sortable selectable={!!selectRows} {...tableProps}>
        <Table.Header>
          <Table.Row>
            {selectRows &&
              <Table.HeaderCell collapsing content={<Checkbox checked={this.allSelected()} indeterminate={this.someSelected()} onClick={this.selectAll} />} />
            }
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
            <Table.Row key={row[idField]} onClick={this.handleSelect(row[idField])} active={selected[row[idField]]}>
              {selectRows && <Table.Cell content={<Checkbox checked={selected[row[idField]]} />} />}
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
