import React from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { connect } from 'react-redux'

import { getLocusListsByGuid } from 'redux/selectors'
import SortableTable from 'shared/components/table/SortableTable'

const BASE_COLUMNS = [
  { name: 'name', width: 3, content: 'List', format: locusList => <Link to={`/gene_lists/${locusList.locusListGuid}`}>{locusList.name}</Link> },
  { name: 'numEntries', width: 1, content: 'Genes' },
  { name: 'description', width: 6, content: 'Description' },
  { name: 'lastModifiedDate', width: 3, content: 'Last Updated', format: locusList => new Date(locusList.lastModifiedDate).toLocaleString() },
]

const PUBLIC_COLUMNS = BASE_COLUMNS.concat([{ name: 'createdBy', width: 3, content: 'Curator' }])
const PRIVATE_COLUMNS = BASE_COLUMNS.concat([{ name: '', width: 3, content: '' }])

const LocusListTable = ({ locusListsByGuid, showPublic }) =>
  <SortableTable
    basic="very"
    fixed
    idField="locusListGuid"
    defaultSortColumn="name"
    columns={showPublic ? PUBLIC_COLUMNS : PRIVATE_COLUMNS}
    data={Object.values(locusListsByGuid).filter(locusList => locusList.isPublic === showPublic)}
  />

LocusListTable.propTypes = {
  locusListsByGuid: PropTypes.object,
  showPublic: PropTypes.bool,
}

const mapStateToProps = state => ({
  locusListsByGuid: getLocusListsByGuid(state),
})

export default connect(mapStateToProps)(LocusListTable)
