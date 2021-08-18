import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Header } from 'semantic-ui-react'

import { getLocusListTableData, getLocusListsIsLoading } from 'redux/selectors'
import { UpdateLocusListButton, DeleteLocusListButton } from '../buttons/LocusListButtons'
import DataTable from './DataTable'
import { VerticalSpacer } from '../Spacers'
import { LOCUS_LIST_FIELDS, LOCUS_LIST_NAME_FIELD, LOCUS_LIST_DESCRIPTION_FIELD } from '../../utils/constants'

const FilterContainer = styled.div`
  position: relative;
  top: -60px;
  margin-bottom: -60px;
  text-align: right;
`

const LOCUS_LIST_TABLE_FIELDS = LOCUS_LIST_FIELDS.map(({ name, label, fieldDisplay, width }) => ({
  name,
  width: Math.min(width, 6),
  content: label,
  format: fieldDisplay ? val => fieldDisplay(val[name]) : null,
}))

const BASIC_FIELDS = LOCUS_LIST_TABLE_FIELDS.slice(0, 3)

const NAME_WITH_LINK_FIELD = {
  ...LOCUS_LIST_TABLE_FIELDS[0],
  format: locusList => <Link to={`/summary_data/gene_lists/${locusList.locusListGuid}`}>{locusList.name}</Link>,
}

const MY_TABLE = {
  name: 'My',
  tableFields: [
    NAME_WITH_LINK_FIELD,
    ...LOCUS_LIST_TABLE_FIELDS.slice(1, 4),
    LOCUS_LIST_TABLE_FIELDS[5],
    {
      name: '',
      format: locusList => ([
        <UpdateLocusListButton key="edit" locusList={locusList} />,
        <DeleteLocusListButton key="delete" iconOnly locusList={locusList} />,
      ]),
      width: 1,
    },
  ],
}
const PUBLIC_TABLE = {
  name: 'Public',
  tableFields: [NAME_WITH_LINK_FIELD, ...LOCUS_LIST_TABLE_FIELDS.slice(1, 5)],
}
const TABLES = [MY_TABLE, PUBLIC_TABLE]

const getLocusListFilterVal = list =>
  [LOCUS_LIST_NAME_FIELD, LOCUS_LIST_DESCRIPTION_FIELD].map(key => list[key] || '').join()

const LocusListTables = React.memo(({ tableData, basicFields, omitLocusLists, tableButtons, ...tableProps }) => {
  return TABLES.map(
    ({ name, tableFields }) =>
      <div key={name}>
        <VerticalSpacer height={5} />
        <Header size="large" dividing content={`${name} Gene Lists`} />
        <DataTable
          basic="very"
          fixed
          idField="locusListGuid"
          defaultSortColumn="name"
          columns={basicFields ? BASIC_FIELDS : tableFields}
          data={tableData[name]}
          getRowFilterVal={getLocusListFilterVal}
          filterContainer={FilterContainer}
          {...tableProps}
        />
        {tableButtons && tableButtons[name]}
      </div>,
  )
})

LocusListTables.propTypes = {
  tableData: PropTypes.object,
  basicFields: PropTypes.bool,
  omitLocusLists: PropTypes.array,
  tableButtons: PropTypes.node,
}


const mapStateToProps = (state, ownProps) => ({
  tableData: getLocusListTableData(state, ownProps),
  loading: getLocusListsIsLoading(state),
})

export default connect(mapStateToProps)(LocusListTables)
