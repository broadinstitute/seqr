import React from 'react'
import PropTypes from 'prop-types'
import sortBy from 'lodash/sortBy'
import styled from 'styled-components'
import { Grid } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { VerticalSpacer } from 'shared/components/Spacers'
import EditDatasetsButton from 'shared/components/buttons/EditDatasetsButton'
import EditFamiliesAndIndividualsButton from 'shared/components/buttons/EditFamiliesAndIndividualsButton'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import {
  SAMPLE_TYPE_LOOKUP,
  DATASET_TYPE_VARIANT_CALLS,
  SAMPLE_STATUS_LOADED,
} from 'shared/utils/constants'
import {
  getAnalysisStatusCounts,
  getProjectAnalysisGroupFamiliesByGuid,
  getProjectAnalysisGroupIndividualsByGuid, getProjectAnalysisGroupSamplesByGuid,
} from '../selectors'

const DetailContent = styled.div`
 padding: 5px 0px 0px 20px;
`

const FAMILY_SIZE_LABELS = {
  0: plural => ` ${plural ? 'families' : 'family'} with no individuals`,
  1: plural => ` ${plural ? 'families' : 'family'} with 1 individual`,
  2: plural => ` ${plural ? 'families' : 'family'} with 2 individuals`,
  3: plural => ` trio${plural ? 's' : ''}`,
  4: plural => ` quad${plural ? 's' : ''}`,
  5: plural => ` ${plural ? 'families' : 'family'} with 5+ individuals`,
}


const ProjectOverview = ({ familiesByGuid, individualsByGuid, samplesByGuid, analysisStatusCounts }) => {
  const familySizeHistogram = Object.values(familiesByGuid)
    .map(family => Math.min(family.individualGuids.length, 5))
    .reduce((acc, familySize) => (
      { ...acc, [familySize]: (acc[familySize] || 0) + 1 }
    ), {})

  const loadedProjectSamples = Object.values(samplesByGuid).filter(sample =>
    sample.datasetType === DATASET_TYPE_VARIANT_CALLS && sample.sampleStatus === SAMPLE_STATUS_LOADED,
  ).reduce((acc, sample) => {
    const loadedDate = new Date(sample.loadedDate).toLocaleDateString()
    const currentDateSamplesByType = acc[loadedDate] || {}
    return { ...acc, [loadedDate]: { ...currentDateSamplesByType, [sample.sampleType]: (currentDateSamplesByType[sample.sampleType] || 0) + 1 } }
  }, {})

  return (
    <Grid>
      <Grid.Column width={5}>
        <b>{Object.keys(familiesByGuid).length} Families, {Object.keys(individualsByGuid).length} Individuals</b>
        <DetailContent>
          {
            sortBy(Object.keys(familySizeHistogram)).map(size =>
              <div key={size}>
                {familySizeHistogram[size]} {FAMILY_SIZE_LABELS[size](familySizeHistogram[size] > 1)}
              </div>)
          }
        </DetailContent>
        <VerticalSpacer height={15} />
        <EditFamiliesAndIndividualsButton />
      </Grid.Column>
      <Grid.Column width={5}>
        <b>Datasets</b>
        <DetailContent>
          {Object.keys(loadedProjectSamples).length > 0 ?
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
        </DetailContent>
        <VerticalSpacer height={15} />
        <EditDatasetsButton />
      </Grid.Column>
      <Grid.Column width={6}>
        <b>Analysis Status</b>
        <DetailContent>
          <HorizontalStackedBar height={20} title="Analysis Statuses" data={analysisStatusCounts} />
        </DetailContent>
      </Grid.Column>
    </Grid>
  )
}


ProjectOverview.propTypes = {
  familiesByGuid: PropTypes.object.isRequired,
  individualsByGuid: PropTypes.object.isRequired,
  samplesByGuid: PropTypes.object.isRequired,
  analysisStatusCounts: PropTypes.array.isRequired,
}

const mapStateToProps = (state, ownProps) => ({
  familiesByGuid: getProjectAnalysisGroupFamiliesByGuid(state, ownProps),
  individualsByGuid: getProjectAnalysisGroupIndividualsByGuid(state, ownProps),
  samplesByGuid: getProjectAnalysisGroupSamplesByGuid(state, ownProps),
  analysisStatusCounts: getAnalysisStatusCounts(state, ownProps),
})

export default connect(mapStateToProps)(ProjectOverview)
