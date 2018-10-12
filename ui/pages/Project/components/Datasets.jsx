import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import {
  SAMPLE_TYPE_LOOKUP,
  DATASET_TYPE_VARIANT_CALLS,
  SAMPLE_STATUS_LOADED,
} from 'shared/utils/constants'
import {
  getProjectAnalysisGroupSamplesByGuid,
} from '../selectors'


const Datasets = ({ samplesByGuid }) => {
  const loadedProjectSamples = Object.values(samplesByGuid).filter(sample =>
    sample.datasetType === DATASET_TYPE_VARIANT_CALLS && sample.sampleStatus === SAMPLE_STATUS_LOADED,
  ).reduce((acc, sample) => {
    const loadedDate = new Date(sample.loadedDate).toLocaleDateString()
    const currentDateSamplesByType = acc[loadedDate] || {}
    return { ...acc, [loadedDate]: { ...currentDateSamplesByType, [sample.sampleType]: (currentDateSamplesByType[sample.sampleType] || 0) + 1 } }
  }, {})

  return Object.keys(loadedProjectSamples).length > 0 ?
    Object.keys(loadedProjectSamples).sort().map(loadedDate => (
      <div key={loadedDate}>
        {
          Object.keys(loadedProjectSamples[loadedDate]).map(currentSampleType =>
            <div key={currentSampleType}>
              {SAMPLE_TYPE_LOOKUP[currentSampleType].text} callset - {loadedProjectSamples[loadedDate][currentSampleType]} samples loaded on {loadedDate}
            </div>,
          )
        }
      </div>
    )) : <div>No Datasets Loaded</div>
}


Datasets.propTypes = {
  samplesByGuid: PropTypes.object.isRequired,
}

const mapStateToProps = (state, ownProps) => ({
  samplesByGuid: getProjectAnalysisGroupSamplesByGuid(state, ownProps),
})

export default connect(mapStateToProps)(Datasets)
