import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { DISCOVERY_SHEET_COLUMNS, CMG_PROJECT_PATH } from '../constants'
import { loadDiscoverySheet } from '../reducers'
import { getDiscoverySheetLoading, getDiscoverySheetLoadingError, getDiscoverySheetRows } from '../selectors'
import BaseReport from './BaseReport'

const getDownloadFilename = projectGuid => `discovery_sheet_${projectGuid}`

const VIEW_ALL_PAGES = [{ name: 'CMG', path: CMG_PROJECT_PATH }]

const DiscoverySheet = React.memo(props => (
  <BaseReport
    page="discovery_sheet"
    viewAllPages={VIEW_ALL_PAGES}
    idField="row_id"
    defaultSortColumn="family_id"
    columns={DISCOVERY_SHEET_COLUMNS}
    getDownloadFilename={getDownloadFilename}
    {...props}
  />
))

DiscoverySheet.propTypes = {
  match: PropTypes.object,
}

const mapStateToProps = state => ({
  data: getDiscoverySheetRows(state),
  loading: getDiscoverySheetLoading(state),
  loadingError: getDiscoverySheetLoadingError(state),
})

const mapDispatchToProps = {
  load: loadDiscoverySheet,
}

export default connect(mapStateToProps, mapDispatchToProps)(DiscoverySheet)
