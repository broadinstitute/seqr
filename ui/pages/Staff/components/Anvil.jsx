import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { loadAnvil } from '../reducers'
import { getAnvilLoading, getAnvilLoadingError, getAnvilRows, getAnvilColumns } from '../selectors'
import BaseReport from './BaseReport'


const getDownloadFilename = (projectGuid, data) => {
  const projectName = projectGuid && projectGuid !== 'all' && data.length && data[0]['Project ID'].replace(/ /g, '_')
  return `${projectName || 'All_AnVIL_Projects'}_${new Date().toISOString().slice(0, 10)}_Metadata`
}

const Anvil = props =>
  <BaseReport
    page="anvil"
    viewAllCategory="AnVIL"
    idField="individualGuid"
    defaultSortColumn="familyId"
    getDownloadFilename={getDownloadFilename}
    {...props}
  />

Anvil.propTypes = {
  match: PropTypes.object,
  data: PropTypes.array,
  columns: PropTypes.array,
  loading: PropTypes.bool,
  loadingError: PropTypes.string,
  load: PropTypes.func,
}

const mapStateToProps = state => ({
  data: getAnvilRows(state),
  columns: getAnvilColumns(state),
  loading: getAnvilLoading(state),
  loadingError: getAnvilLoadingError(state),
})

const mapDispatchToProps = {
  load: loadAnvil,
}

export default connect(mapStateToProps, mapDispatchToProps)(Anvil)
