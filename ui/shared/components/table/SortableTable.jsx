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
    selectedRows: PropTypes.object,
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

  allSelected = () => (
    this.props.data.length > 0 &&
    Object.keys(this.props.selectedRows).length === this.props.data.length &&
    Object.values(this.props.selectedRows).every(isSelected => isSelected)
  )
  someSelected = () => Object.values(this.props.selectedRows).includes(true) && Object.values(this.props.selectedRows).includes(false)

  selectAll = () => {
    if (!this.props.selectRows) {
      return
    }

    const rowIds = this.props.data.map(row => row[this.props.idField])
    const allSelected = !this.allSelected()
    this.props.selectRows(rowIds.reduce((acc, rowId) => ({ ...acc, [rowId]: allSelected }), {}))
  }

  handleSelect = rowId => () => {
    if (!this.props.selectRows) {
      return
    }

    this.props.selectRows({ ...this.props.selectedRows, [rowId]: !this.props.selectedRows[rowId] })
  }

  render() {
    const { data, defaultSortColumn, idField, columns, selectRows, selectedRows = {}, ...tableProps } = this.props
    const { column, direction } = this.state

    let sortedData = data.sort(compareObjects(column))
    if (direction === DESCENDING) {
      sortedData = sortedData.reverse()
    }

    return (
      <StyledSortableTable sortable selectable={!!selectRows} {...tableProps}>
        <Table.Header>
          <Table.Row>
            {selectRows &&
              <Table.HeaderCell width={1} content={<Checkbox checked={this.allSelected()} indeterminate={this.someSelected()} onClick={this.selectAll} />} />
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
            <Table.Row key={row[idField]} onClick={this.handleSelect(row[idField])} active={selectedRows[row[idField]]}>
              {selectRows && <Table.Cell content={<Checkbox checked={selectedRows[row[idField]]} />} />}
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

const EMPTY_OBJECT = {}
export const SelectableTableFormInput = ({ value, onChange, error, ...props }) =>
  <SortableTable
    basic="very"
    fixed
    selectRows={onChange}
    selectedRows={value || EMPTY_OBJECT}
    {...props}
  />

SelectableTableFormInput.propTypes = {
  value: PropTypes.any,
  onChange: PropTypes.func,
  error: PropTypes.bool,
}
