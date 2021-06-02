import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Table, Checkbox, Pagination, Form } from 'semantic-ui-react'

import { compareObjects } from '../../utils/sortUtils'
import ExportTableButton from '../buttons/ExportTableButton'
import { configuredField } from '../form/ReduxFormWrapper'
import TableLoading from './TableLoading'

const TableContainer = styled.div`
  overflow-x: ${props => (props.horizontalScroll ? 'scroll' : 'inherit')};
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

const getRowColumnContent = (row, isExport) => col => ((col.format && !(isExport && col.noFormatExport)) ? col.format(row, isExport) : row[col.name])

class DataTable extends React.PureComponent {

  static propTypes = {
    data: PropTypes.array,
    columns: PropTypes.array,
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
    fixedWidth: PropTypes.bool,
    downloadTableType: PropTypes.string,
    downloadFileName: PropTypes.string,
    downloadAlign: PropTypes.string,
    loadingProps: PropTypes.object,
  }

  static defaultProps = {
    selectedRows: {},
  }

  constructor(props) {
    super(props)

    this.state = {
      column: props.defaultSortColumn,
      direction: props.defaultSortDescending ? DESCENDING : ASCENDING,
      activePage: 1,
      filter: null,
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

  handleFilter = (e, data) => {
    this.setState({ filter: data.value.toLowerCase() })
  }

  allSelected = () => (
    this.props.data.length > 0 &&
    Object.keys(this.props.selectedRows).length === this.props.data.length &&
    Object.values(this.props.selectedRows).every(isSelected => isSelected)
  )

  someSelected = () =>
    this.props.data.some(row => this.props.selectedRows[row[this.props.idField]]) &&
    this.props.data.some(row => !this.props.selectedRows[row[this.props.idField]])

  selectAll = () => {
    if (!this.props.selectRows) {
      return
    }

    const allSelected = !this.allSelected()
    this.props.selectRows(
      this.props.data.reduce((acc, row) => (
        { ...acc, [row[this.props.idField]]: (allSelected && this.props.includeSelectedRowData) ? row : allSelected }
      ), {}))
  }

  handleSelect = rowId => () => {
    if (!this.props.selectRows) {
      return
    }

    let newSelected = !this.props.selectedRows[rowId]
    if (newSelected && this.props.includeSelectedRowData) {
      newSelected = this.props.data.find(row => row[this.props.idField] === rowId)
    }

    this.props.selectRows({ ...this.props.selectedRows, [rowId]: newSelected })
  }

  render() {
    const {
      data, defaultSortColumn, defaultSortDescending, getRowFilterVal, idField, columns, selectRows, selectedRows = {},
      loading, emptyContent, footer, rowsPerPage, horizontalScroll, downloadFileName, downloadTableType, downloadAlign,
      fixedWidth, includeSelectedRowData, loadingProps = {}, ...tableProps
    } = this.props
    const { column, direction, activePage, filter } = this.state

    let totalRows = data.length
    let sortedData = data.sort(compareObjects(column))
    if (direction === DESCENDING) {
      sortedData = sortedData.reverse()
    }

    let exportConfig
    if (downloadFileName) {
      exportConfig = [
        {
          name: downloadTableType || 'All Data',
          data: {
            filename: downloadFileName,
            rawData: sortedData,
            headers: columns.map(config => config.downloadColumn || config.content),
            processRow: row => columns.map(getRowColumnContent(row, true)),
          },
        },
      ]
    }

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
          {processedColumns.map(({ name, format, textAlign, verticalAlign }) =>
            <Table.Cell
              key={name}
              content={getRowColumnContent(row)({ format, name })}
              textAlign={textAlign}
              verticalAlign={verticalAlign}
            />,
          )}
        </Table.Row>
      ))
    }

    const hasFooter = footer || isPaginated
    const filterInput = getRowFilterVal && <Form.Input label="Filter: " inline onChange={this.handleFilter} />

    return (
      <TableContainer horizontalScroll={horizontalScroll}>
        {!hasFooter && filterInput}
        {exportConfig &&
          <RightAligned topAlign={downloadAlign}>
            <ExportTableButton downloads={exportConfig} />
          </RightAligned>
        }
        <StyledDataTable
          sortable
          selectable={!!selectRows}
          columns={!tableProps.collapsing && !fixedWidth && columns.length <= 16 ? columns.length : null}
          attached={hasFooter && 'top'}
          {...tableProps}
        >
          <Table.Header>
            <Table.Row>
              {selectRows &&
                <Table.HeaderCell width={1} content={<Checkbox checked={this.allSelected()} indeterminate={this.someSelected()} onClick={this.selectAll} />} />
              }
              {processedColumns.map(({ name, format, noFormatExport, ...columnProps }) =>
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
        </StyledDataTable>
        {hasFooter &&
          <Table {...tableProps} fixed={false} attached="bottom">
            <Table.Footer>
              <Table.Row>
                {footer && <Table.HeaderCell collapsing={rowsPerPage} content={footer} />}
                {filterInput && <Table.HeaderCell collapsing>{filterInput}</Table.HeaderCell>}
                <Table.HeaderCell collapsing={!rowsPerPage} textAlign="right">
                  {isPaginated &&
                    <div>
                      Showing rows {((activePage - 1) * rowsPerPage) + 1}-{Math.min(activePage * rowsPerPage, totalRows)}
                      &nbsp; &nbsp;
                      <Pagination
                        activePage={activePage}
                        totalPages={Math.ceil(totalRows / rowsPerPage)}
                        onPageChange={(e, d) => this.setState({ activePage: d.activePage })}
                        size="mini"
                      />
                    </div>
                  }
                </Table.HeaderCell>
              </Table.Row>
            </Table.Footer>
          </Table>
        }
      </TableContainer>
    )
  }
}

export default DataTable

const EMPTY_OBJECT = {}
export const SelectableTableFormInput = React.memo(({ value, onChange, error, data = [], ...props }) =>
  <DataTable
    basic="very"
    fixed
    selectRows={onChange}
    selectedRows={value || EMPTY_OBJECT}
    data={data}
    {...props}
  />,
)

SelectableTableFormInput.propTypes = {
  value: PropTypes.any,
  onChange: PropTypes.func,
  error: PropTypes.bool,
  data: PropTypes.array,
}
