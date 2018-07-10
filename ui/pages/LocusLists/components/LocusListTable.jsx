import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { getLocusListsByGuid } from 'redux/selectors'
import SortableTable from 'shared/components/table/SortableTable'

import { LOCUS_LIST_FIELDS } from 'shared/utils/constants'

const FIELDS = LOCUS_LIST_FIELDS.filter(field => field.name !== 'isPublic').map(
  ({ name, label, fieldDisplay, width }) => ({
    name,
    width: Math.min(width, 6),
    content: label,
    format: fieldDisplay ? val => fieldDisplay(val[name]) : null,
  }),
)

FIELDS[0].format = locusList => <Link to={`/gene_lists/${locusList.locusListGuid}`}>{locusList.name}</Link>

export const PRIVATE_FIELDS = FIELDS.slice(0, FIELDS.length - 1).concat([{ name: '', content: '', width: 3 }])

const LocusListTable = ({ locusListsByGuid, showPublic }) =>
  <SortableTable
    basic="very"
    fixed
    idField="locusListGuid"
    defaultSortColumn="name"
    columns={showPublic ? FIELDS : PRIVATE_FIELDS}
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
