import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Header } from 'semantic-ui-react'

import { getLocusListsByGuid, getLocusListsIsLoading, getUser } from 'redux/selectors'
import { UpdateLocusListButton, DeleteLocusListButton } from '../buttons/LocusListButtons'
import DataTable from './DataTable'
import { VerticalSpacer } from '../Spacers'
import {
  LOCUS_LIST_FIELDS, LOCUS_LIST_NAME_FIELD, LOCUS_LIST_NUM_ENTRIES_FIELD, LOCUS_LIST_LAST_MODIFIED_FIELD_NAME,
  LOCUS_LIST_DESCRIPTION_FIELD, LOCUS_LIST_IS_PUBLIC_FIELD_NAME, LOCUS_LIST_CURATOR_FIELD_NAME,
} from '../../utils/constants'

const EDIT_FIELD = 'edit'
const NAME_WITH_LINK_FIELD = 'nameWithLink'
const NUM_PROJECTS_FIELD = 'numProjects'

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
FIELD_LOOKUP[NAME_WITH_LINK_FIELD] = {
  ...FIELD_LOOKUP[LOCUS_LIST_NAME_FIELD],
  format: locusList => <Link to={`/gene_lists/${locusList.locusListGuid}`}>{locusList.name}</Link>,
}
FIELD_LOOKUP[EDIT_FIELD] = {
  name: '',
  format: locusList => ([
    <UpdateLocusListButton key="edit" locusList={locusList} />,
    <DeleteLocusListButton key="delete" iconOnly locusList={locusList} />,
  ]),
  width: 1,
}
FIELD_LOOKUP[NUM_PROJECTS_FIELD] = {
  name: NUM_PROJECTS_FIELD,
  content: 'Projects',
  width: 1,
  format: null,
}

const CORE_FIELDS = [
  NAME_WITH_LINK_FIELD, LOCUS_LIST_NUM_ENTRIES_FIELD, LOCUS_LIST_DESCRIPTION_FIELD, LOCUS_LIST_LAST_MODIFIED_FIELD_NAME,
  NUM_PROJECTS_FIELD,
]

const MY_TABLE = {
  name: 'My',
  tableFields: [...CORE_FIELDS, LOCUS_LIST_IS_PUBLIC_FIELD_NAME, EDIT_FIELD],
}
const PUBLIC_TABLE = {
  name: 'Public',
  tableFields: [...CORE_FIELDS, LOCUS_LIST_CURATOR_FIELD_NAME],
}
const EDITABLE_PUBLIC_TABLE = { ...PUBLIC_TABLE, tableFields: [...PUBLIC_TABLE.tableFields, EDIT_FIELD] }
const TABLES = [MY_TABLE, PUBLIC_TABLE]
const PRIVATE_LIST_TABLES = [MY_TABLE, EDITABLE_PUBLIC_TABLE, {
  name: 'Private',
  tableFields: [...CORE_FIELDS, LOCUS_LIST_CURATOR_FIELD_NAME],
}]

const LocusListTables = React.memo(({ locusListsByGuid, fields, omitLocusLists, hidePrivateLists, user, ...tableProps }) => {
  let data = Object.values(locusListsByGuid)
  if (omitLocusLists) {
    data = data.filter(locusList => !omitLocusLists.includes(locusList.locusListGuid))
  }

  const tableData = data.reduce((acc, locusList) => {
    if (locusList.canEdit) {
      acc.My.push(locusList)
    } else if (locusList.isPublic) {
      acc.Public.push(locusList)
    } else {
      acc.Private.push(locusList)
    }
    return acc
  }, { My: [], Public: [], Private: [] })

  return ((!hidePrivateLists && user.isStaff) ? PRIVATE_LIST_TABLES : TABLES).map(
    ({ name, tableFields }) =>
      <div key={name}>
        <VerticalSpacer height={5} />
        <Header size="large" dividing content={`${name} Gene Lists`} />
        <DataTable
          basic="very"
          fixed
          idField="locusListGuid"
          defaultSortColumn="name"
          columns={(fields || tableFields).map(field => FIELD_LOOKUP[field])}
          data={tableData[name]}
          {...tableProps}
        />
      </div>,
  )
})

LocusListTables.propTypes = {
  locusListsByGuid: PropTypes.object,
  fields: PropTypes.array,
  omitLocusLists: PropTypes.array,
  hidePrivateLists: PropTypes.bool,
  user: PropTypes.object,
}


const mapStateToProps = state => ({
  locusListsByGuid: getLocusListsByGuid(state),
  loading: getLocusListsIsLoading(state),
  user: getUser(state),
})

export default connect(mapStateToProps)(LocusListTables)
