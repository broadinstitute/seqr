import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Header } from 'semantic-ui-react'

import { getLocusListTableData, getLocusListsIsLoading } from 'redux/selectors'
import { UpdateLocusListButton, DeleteLocusListButton } from '../buttons/LocusListButtons'
import { SelectableTableFormInput } from './DataTable'
import { VerticalSpacer } from '../Spacers'
import {
  LOCUS_LIST_FIELDS, LOCUS_LIST_NAME_FIELD, LOCUS_LIST_NUM_ENTRIES_FIELD, LOCUS_LIST_LAST_MODIFIED_FIELD_NAME,
  LOCUS_LIST_DESCRIPTION_FIELD, LOCUS_LIST_IS_PUBLIC_FIELD_NAME, LOCUS_LIST_CURATOR_FIELD_NAME,
  LOCUS_LIST_CREATED_DATE_FIELD_NAME,
} from '../../utils/constants'

const FilterContainer = styled.div`
  position: relative;
  top: -60px;
  margin-bottom: -60px;
  text-align: right;
`

const FIELD_LOOKUP = LOCUS_LIST_FIELDS.reduce(
  (acc, { name, label, fieldDisplay, width }) => ({
    ...acc,
    [name]: {
      name,
      width: Math.min(width, 6),
      content: label,
      format: fieldDisplay ? val => fieldDisplay(val[name]) : null,
    },
  }), {},
)

const BASIC_FIELDS = [LOCUS_LIST_NAME_FIELD, LOCUS_LIST_DESCRIPTION_FIELD, LOCUS_LIST_CREATED_DATE_FIELD_NAME,
  LOCUS_LIST_NUM_ENTRIES_FIELD].map(
  field => FIELD_LOOKUP[field],
)

const NAME_WITH_LINK_FIELD = {
  ...FIELD_LOOKUP[LOCUS_LIST_NAME_FIELD],
  format: locusList => <Link to={`/summary_data/gene_lists/${locusList.locusListGuid}`}>{locusList.name}</Link>,
}

const CORE_FIELDS = [
  NAME_WITH_LINK_FIELD,
  ...[LOCUS_LIST_NUM_ENTRIES_FIELD, LOCUS_LIST_DESCRIPTION_FIELD, LOCUS_LIST_CREATED_DATE_FIELD_NAME,
    LOCUS_LIST_LAST_MODIFIED_FIELD_NAME].map(
    field => FIELD_LOOKUP[field],
  ), { name: 'numProjects', content: 'Projects', width: 1, format: null },
]

const MY_TABLE = {
  name: 'My',
  tableFields: [
    ...CORE_FIELDS,
    FIELD_LOOKUP[LOCUS_LIST_IS_PUBLIC_FIELD_NAME],
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
  tableFields: [...CORE_FIELDS, FIELD_LOOKUP[LOCUS_LIST_CURATOR_FIELD_NAME]],
}
const TABLES = [MY_TABLE, PUBLIC_TABLE]

const getLocusListFilterVal = list => [
  list[LOCUS_LIST_NAME_FIELD], list[LOCUS_LIST_DESCRIPTION_FIELD] || '', ...(list.geneNames || []),
].join()

const LocusListTables = React.memo(
  ({ tableData, basicFields, tableButtons, dispatch, ...tableProps }) => TABLES.map(
    ({ name, tableFields }) => (
      <div key={name}>
        <VerticalSpacer height={5} />
        <Header size="large" dividing content={`${name} Gene Lists`} />
        <SelectableTableFormInput
          idField="locusListGuid"
          defaultSortColumn="createdDate"
          defaultSortDescending
          columns={basicFields ? BASIC_FIELDS : tableFields}
          data={tableData[name]}
          getRowFilterVal={getLocusListFilterVal}
          filterContainer={FilterContainer}
          {...tableProps}
        />
        {tableButtons && tableButtons[name]}
      </div>
    ),
  ),
)

LocusListTables.propTypes = {
  tableData: PropTypes.object,
  basicFields: PropTypes.bool,
  tableButtons: PropTypes.object,
  dispatch: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  tableData: getLocusListTableData(state, ownProps),
  loading: getLocusListsIsLoading(state),
})

export default connect(mapStateToProps)(LocusListTables)
