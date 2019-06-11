import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { BaseSemanticInput } from 'shared/components/form/Inputs'
import { loadAnvil } from '../reducers'
import { getAnvilLoading, getAnvilLoadingError, getAnvilRows, getAnvilColumns } from '../selectors'
import BaseReport from './BaseReport'

const getDownloadFilename = (projectGuid, data) => {
  const projectName = projectGuid && projectGuid !== 'all' && data.length && data[0].Project_ID.replace(/ /g, '_')
  return `${projectName || 'All_AnVIL_Projects'}_${new Date().toISOString().slice(0, 10)}_Metadata`
}

const FIELDS = [
  {
    name: 'loadedBefore',
    label: 'Loaded Before',
    inline: true,
    component: BaseSemanticInput,
    inputType: 'Input',
    type: 'date',
  },
]

const AnvilFilters = ({ load, match }) =>
  <ReduxFormWrapper
    onSubmit={values => load(match.params.projectGuid, values)}
    form="anvilFilters"
    fields={FIELDS}
    noModal
    inline
    submitOnChange
  />

AnvilFilters.propTypes = {
  match: PropTypes.object,
  load: PropTypes.func,
}

const Anvil = props =>
  <BaseReport
    page="anvil"
    viewAllCategory="AnVIL"
    idField="individualGuid"
    defaultSortColumn="familyId"
    getDownloadFilename={getDownloadFilename}
    filters={<AnvilFilters {...props} />}
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
