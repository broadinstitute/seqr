import React from 'react'
import PropTypes from 'prop-types'
import sortBy from 'lodash/sortBy'
import styled from 'styled-components'
import { Grid } from 'semantic-ui-react'
import { connect } from 'react-redux'

import EditFamiliesAndIndividualsButton from 'shared/components/buttons/EditFamiliesAndIndividualsButton'
import EditDatasetsButton from 'shared/components/buttons/EditDatasetsButton'
import { SAMPLE_TYPE_LOOKUP, DATASET_TYPE_VARIANT_CALLS, SAMPLE_STATUS_LOADED } from 'shared/utils/constants'
import { getProject, getProjectFamiliesByGuid, getProjectIndividualsByGuid, getProjectSamplesByGuid } from '../selectors'


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


const ProjectOverview = ({ project, familiesByGuid, individualsByGuid, samplesByGuid }) => {
  const familySizeHistogram = Object.values(familiesByGuid)
    .map(family => Math.min(family.individualGuids.length, 5))
    .reduce((acc, familySize) => (
      { ...acc, [familySize]: (acc[familySize] || 0) + 1 }
    ), {})

  const loadedProjectSamples = Object.values(samplesByGuid).filter(sample =>
    sample.datasetType === DATASET_TYPE_VARIANT_CALLS && sample.sampleStatus === SAMPLE_STATUS_LOADED,
  ).reduce((acc, sample) => {
    const loadedDate = new Date(sample.loadedDate).toLocaleDateString()
    const sampleTypeByDate = acc[sample.sampleType] || {}
    return { ...acc, [sample.sampleType]: { ...sampleTypeByDate, [loadedDate]: (sampleTypeByDate[loadedDate] || 0) + 1 } }
  }, {})

  return (
    <Grid>
      <Grid.Row>
        <Grid.Column width={5}>
          {Object.keys(familiesByGuid).length} Families, {Object.keys(individualsByGuid).length} Individuals
          <DetailContent>
            {
              sortBy(Object.keys(familySizeHistogram)).map(size =>
                <div key={size}>
                  {familySizeHistogram[size]} {FAMILY_SIZE_LABELS[size](familySizeHistogram[size] > 1)}
                </div>)
            }
            {project.canEdit ? <span><br /><EditFamiliesAndIndividualsButton /></span> : null }<br />
          </DetailContent>
        </Grid.Column>
        <Grid.Column width={11}>
          Datasets:
          <DetailContent>
            {
              Object.keys(loadedProjectSamples).length > 0 ?
                Object.keys(loadedProjectSamples).map(currentSampleType => (
                  <div key={currentSampleType}>
                    {
                      Object.keys(loadedProjectSamples[currentSampleType]).map(loadedDate =>
                        <div key={loadedDate}>
                          {SAMPLE_TYPE_LOOKUP[currentSampleType].text} callset - {loadedProjectSamples[currentSampleType][loadedDate]} samples loaded on {loadedDate}
                        </div>,
                      )
                    }
                  </div>
                )) : <div>No Datasets Loaded</div>
            }
            {project.canEdit ? <span><br /><EditDatasetsButton /></span> : null }<br />
          </DetailContent>
        </Grid.Column>
      </Grid.Row>
    </Grid>
  )
}


ProjectOverview.propTypes = {
  project: PropTypes.object,
  familiesByGuid: PropTypes.object.isRequired,
  individualsByGuid: PropTypes.object.isRequired,
  samplesByGuid: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
  familiesByGuid: getProjectFamiliesByGuid(state),
  individualsByGuid: getProjectIndividualsByGuid(state),
  samplesByGuid: getProjectSamplesByGuid(state),
})


export { ProjectOverview as ProjectOverviewComponent }

export default connect(mapStateToProps)(ProjectOverview)
