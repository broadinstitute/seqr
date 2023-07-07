import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Table, Checkbox, Pagination, Form } from 'semantic-ui-react'

import { compareObjects } from '../../utils/sortUtils'
import ExportTableButton from '../buttons/ExportTableButton'
import { configuredField } from '../form/FormHelpers'
import TableLoading from './TableLoading'

const TableContainer = styled.div`
  overflow-x: ${props => (props.horizontalScroll ? 'scroll' : 'inherit')};
  overflow-y: ${props => (props.maxHeight ? 'auto' : 'inherit')};
  max-height: ${props => (props.maxHeight || 'inherit')};
`

const RightAligned = styled.span`
  position: absolute;
  right: 20px;
  top: ${props => (props.topAlign || '30px')};
`

const StyledDataTable = styled(Table)`
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

const getRowColumnContent = (row, isExport) => (col, formatProps) => (
  (col.format && !(isExport && col.noFormatExport)) ? col.format(row, isExport, formatProps) : row[col.name])

class DataTable extends React.PureComponent {

  static propTypes = {
    data: PropTypes.arrayOf(PropTypes.object),
    columns: PropTypes.arrayOf(PropTypes.object),
    idField: PropTypes.string.isRequired,
    defaultSortColumn: PropTypes.string,
    defaultSortDescending: PropTypes.bool,
    getRowFilterVal: PropTypes.func,
    selectRows: PropTypes.func,
    selectedRows: PropTypes.object,
    includeSelectedRowData: PropTypes.bool,
    loading: PropTypes.bool,
    emptyContent: PropTypes.node,
    footer: PropTypes.node,
    rowsPerPage: PropTypes.number,
    horizontalScroll: PropTypes.bool,
    maxHeight: PropTypes.string,
    fixedWidth: PropTypes.bool,
    downloadTableType: PropTypes.string,
    downloadFileName: PropTypes.string,
    downloadAlign: PropTypes.string,
    loadingProps: PropTypes.object,
    filterContainer: PropTypes.object,
    // eslint-disable-next-line react/forbid-prop-types
    formatProps: PropTypes.any,
  }

  static defaultProps = {
    selectedRows: {},
    data: [],
  }

  state = {
    column: null,
    direction: null,
    activePage: 1,
    filter: null,
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

  handleFilter = (e, data) => {
    this.setState({ filter: data.value.toLowerCase() })
  }

  allSelected = () => {
    const { data, selectedRows } = this.props
    return data.length > 0 && Object.keys(selectedRows).length === data.length &&
      Object.values(selectedRows).every(isSelected => isSelected)
  }

  someSelected = () => {
    const { data, selectedRows, idField } = this.props
    return data.some(row => selectedRows[row[idField]]) && data.some(row => !selectedRows[row[idField]])
  }

  selectAll = () => {
    const { data, selectRows, includeSelectedRowData, idField } = this.props
    if (!selectRows) {
      return
    }

    const allSelected = !this.allSelected()
    selectRows(
      data.reduce((acc, row) => (
        { ...acc, [row[idField]]: (allSelected && includeSelectedRowData) ? row : allSelected }
      ), {}),
    )
  }

  handleSelect = rowId => () => {
    const { data, selectRows, selectedRows, includeSelectedRowData, idField } = this.props
    if (!selectRows) {
      return
    }

    let newSelected = !selectedRows[rowId]
    if (newSelected && includeSelectedRowData) {
      newSelected = data.find(row => row[idField] === rowId)
    }

    selectRows({ ...selectedRows, [rowId]: newSelected })
  }

  handlePageChange = (e, d) => this.setState({ activePage: d.activePage })

  exportConfig = (sortedData) => {
    const { columns, downloadFileName, downloadTableType } = this.props
    if (!downloadFileName) {
      return null
    }
    return [
      {
        name: downloadTableType || 'All Data',
        filename: downloadFileName,
        rawData: sortedData,
        headers: columns.map(config => config.downloadColumn || config.content),
        processRow: row => columns.map(getRowColumnContent(row, true)),
      },
    ]
  }

  render() {
    const {
      data = [], defaultSortColumn, defaultSortDescending, idField, columns, selectRows, selectedRows = {},
      loading, emptyContent, footer, rowsPerPage, horizontalScroll, downloadFileName, downloadTableType, downloadAlign,
      fixedWidth, includeSelectedRowData, filterContainer, getRowFilterVal, loadingProps = {}, maxHeight,
      formatProps, ...tableProps
    } = this.props
    const { column, direction, activePage, filter } = this.state
    const sortedDirection = direction || (defaultSortDescending ? DESCENDING : ASCENDING)

    let totalRows = data.length
    let sortedData = data.sort(compareObjects(column || defaultSortColumn))
    if (sortedDirection === DESCENDING) {
      sortedData = sortedData.reverse()
    }

    const exportConfig = this.exportConfig(sortedData)

    if (filter) {
      sortedData = sortedData.filter(row => getRowFilterVal(row).toLowerCase().includes(filter))
      totalRows = sortedData.length
    }
    const isPaginated = rowsPerPage && sortedData.length > rowsPerPage
    if (isPaginated) {
      sortedData = sortedData.slice((activePage - 1) * rowsPerPage, activePage * rowsPerPage)
    }

    const processedColumns = columns.map(({ formFieldProps, downloadColumn, ...columnProps }) => (
      formFieldProps ?
        {
          ...columnProps,
          format: row => configuredField({ ...formFieldProps, name: `${row[idField]}.${columnProps.name}`, onClick: e => e.stopPropagation() }),
        } : columnProps
    ))

    let tableContent
    if (loading) {
      tableContent = <TableLoading numCols={columns.length} {...loadingProps} />
    } else if (emptyContent && data.length === 0) {
      tableContent = <Table.Row><Table.Cell colSpan={columns.length}>{emptyContent}</Table.Cell></Table.Row>
    } else {
      tableContent = sortedData.map(row => (
        <Table.Row key={row[idField]} onClick={this.handleSelect(row[idField])} active={!!selectedRows[row[idField]]}>
          {selectRows && <Table.Cell content={<Checkbox checked={!!selectedRows[row[idField]]} />} />}
          {processedColumns.map(({ name, format, textAlign, verticalAlign }) => (
            <Table.Cell
              key={name}
              content={getRowColumnContent(row)({ format, name }, formatProps)}
              textAlign={textAlign}
              verticalAlign={verticalAlign}
            />
          ))}
        </Table.Row>
      ))
    }

    const hasFooter = footer || isPaginated
    const filterInput = getRowFilterVal && <Form.Input label="Filter: " inline onChange={this.handleFilter} />
    const rowSummary = `${((activePage - 1) * rowsPerPage) + 1}-${Math.min(activePage * rowsPerPage, totalRows)}`

    return (
      <TableContainer horizontalScroll={horizontalScroll} maxHeight={maxHeight}>
        {!hasFooter && (filterContainer ? React.createElement(filterContainer, {}, filterInput) : filterInput)}
        {exportConfig &&
          <RightAligned topAlign={downloadAlign}><ExportTableButton downloads={exportConfig} /></RightAligned>}
        <StyledDataTable
          sortable
          selectable={!!selectRows}
          columns={!tableProps.collapsing && !fixedWidth && columns.length <= 16 ? columns.length : null}
          attached={hasFooter && 'top'}
          {...tableProps}
        >
          <Table.Header>
            <Table.Row>
              {selectRows && (
                <Table.HeaderCell
                  width={1}
                  content={
                    <Checkbox
                      checked={this.allSelected()}
                      indeterminate={this.someSelected()}
                      onClick={this.selectAll}
                    />
                  }
                />
              )}
              {processedColumns.map(({ name, format, noFormatExport, ...columnProps }) => (
                <Table.HeaderCell
                  key={name}
                  sorted={(column || defaultSortColumn) === name ? sortedDirection : null}
                  onClick={this.handleSort(name)}
                  {...columnProps}
                />
              ))}
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {tableContent}
          </Table.Body>
        </StyledDataTable>
        {hasFooter && (
          <Table {...tableProps} fixed={false} attached="bottom">
            <Table.Footer>
              <Table.Row>
                {footer && <Table.HeaderCell collapsing={rowsPerPage} content={footer} />}
                {filterInput && <Table.HeaderCell collapsing>{filterInput}</Table.HeaderCell>}
                <Table.HeaderCell collapsing={!rowsPerPage} textAlign="right">
                  {isPaginated && (
                    <div>
                      {`Showing rows ${rowSummary}  `}
                      <Pagination
                        activePage={activePage}
                        totalPages={Math.ceil(totalRows / rowsPerPage)}
                        onPageChange={this.handlePageChange}
                        size="mini"
                      />
                    </div>
                  )}
                </Table.HeaderCell>
              </Table.Row>
            </Table.Footer>
          </Table>
        )}
      </TableContainer>
    )
  }

}

export default DataTable

const EMPTY_OBJECT = {}
export const SelectableTableFormInput = React.memo(({ value, onChange, error, data, ...props }) => (
  <DataTable
    basic="very"
    fixed
    selectRows={onChange}
    selectedRows={value || EMPTY_OBJECT}
    data={data}
    {...props}
  />
))

SelectableTableFormInput.propTypes = {
  value: PropTypes.object,
  onChange: PropTypes.func,
  error: PropTypes.bool,
  data: PropTypes.arrayOf(PropTypes.object),
}
