import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Table, Checkbox } from 'semantic-ui-react'

import { compareObjects } from '../../utils/sortUtils'
import TableLoading from './TableLoading'

const StyledSortableTable = styled(Table)`
  &.ui.sortable.table thead th {
    border-left: none;
    overflow: initial;
    
    &.sorted {
      background: #F9FAFB;
    }
  }
  
  &.ui.basic.sortable.table thead th {
    background: transparent !important;
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
    loading: PropTypes.bool,
    emptyContent: PropTypes.node,
    footer: PropTypes.node,
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

    const selected = !this.state.selected[rowId]
    this.props.selectRows([rowId], selected)
    this.setState({ selected: { ...this.state.selected, [rowId]: selected } })
  }

  render() {
    const { data, defaultSortColumn, idField, columns, selectRows, selectedRows = {}, loading, emptyContent, footer, ...tableProps } = this.props
    const { column, direction } = this.state

    let sortedData = data.sort(compareObjects(column))
    if (direction === DESCENDING) {
      sortedData = sortedData.reverse()
    }

    let tableContent
    if (loading) {
      tableContent = <TableLoading numCols={columns.length} />
    } else if (emptyContent && data.length === 0) {
      tableContent = <Table.Row><Table.Cell colSpan={columns.length}>{emptyContent}</Table.Cell></Table.Row>
    } else {
      tableContent = sortedData.map(row => (
        <Table.Row key={row[idField]} onClick={this.handleSelect(row[idField])} active={selectedRows[row[idField]]}>
          {selectRows && <Table.Cell content={<Checkbox checked={selectedRows[row[idField]]} />} />}
          {columns.map(({ name, format, textAlign }) =>
            <Table.Cell
              key={name}
              content={format ? format(row) : row[name]}
              textAlign={textAlign}
            />,
          )}
        </Table.Row>
      ))
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
          {tableContent}
        </Table.Body>
        {footer &&
          <Table.Footer>
            <Table.Row>
              <Table.HeaderCell colSpan={columns.length} content={footer} />
            </Table.Row>
          </Table.Footer>
        }
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
