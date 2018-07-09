import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getLocusListsByGuid } from 'redux/selectors'
import SortableTable from 'shared/components/table/SortableTable'

import { PUBLIC_COLUMNS, PRIVATE_COLUMNS } from '../constants'

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
