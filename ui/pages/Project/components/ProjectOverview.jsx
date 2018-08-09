import React from 'react'
import PropTypes from 'prop-types'
import sortBy from 'lodash/sortBy'
import styled from 'styled-components'
import { Link } from 'react-router-dom'
import { Grid, Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'

import EditFamiliesAndIndividualsButton from 'shared/components/buttons/EditFamiliesAndIndividualsButton'
import EditDatasetsButton from 'shared/components/buttons/EditDatasetsButton'
import { HelpIcon } from 'shared/components/StyledComponents'
import {
  SAMPLE_TYPE_LOOKUP,
  DATASET_TYPE_VARIANT_CALLS,
  SAMPLE_STATUS_LOADED,
} from 'shared/utils/constants'
import { compareObjects } from 'shared/utils/sortUtils'
import {
  getProject,
  getProjectAnalysisGroupFamiliesByGuid,
  getProjectAnalysisGroupIndividualsByGuid,
  getProjectAnalysisGroupSamplesByGuid,
  getProjectAnalysisGroupsByGuid,
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

// TODO section edit buttons

const ProjectOverview = ({ project, analysisGroup, familiesByGuid, individualsByGuid, samplesByGuid, analysisGroupsByGuid }) => {
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
        {!analysisGroup &&
          <Grid.Column width={5}>
            {Object.keys(analysisGroupsByGuid).length} Analysis Groups
            <DetailContent>
              {
                Object.values(analysisGroupsByGuid).sort(compareObjects('name')).map(ag =>
                  <div key={ag.name}>
                    <Link to={`/project/${project.projectGuid}/analysis_group/${ag.analysisGroupGuid}`}>{ag.name}</Link>
                    <Popup
                      position="right center"
                      trigger={<HelpIcon />}
                      content={<div><b>{ag.familyGuids.length} Families</b><br /><i>{ag.description}</i></div>}
                      size="small"
                    />
                    {/* TODO edit/ remove */}
                  </div>)
              }
              {project.canEdit ? <span><br /><EditFamiliesAndIndividualsButton /></span> : null}<br />
            </DetailContent>
          </Grid.Column>
        }
        <Grid.Column width={analysisGroup ? 11 : 6}>
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
  analysisGroup: PropTypes.object,
  familiesByGuid: PropTypes.object.isRequired,
  individualsByGuid: PropTypes.object.isRequired,
  samplesByGuid: PropTypes.object.isRequired,
  analysisGroupsByGuid: PropTypes.object.isRequired,
}

const mapStateToProps = (state, ownProps) => ({
  project: getProject(state),
  analysisGroup: getProjectAnalysisGroupsByGuid(state)[ownProps.analysisGroupGuid],
  familiesByGuid: getProjectAnalysisGroupFamiliesByGuid(state, ownProps),
  individualsByGuid: getProjectAnalysisGroupIndividualsByGuid(state, ownProps),
  samplesByGuid: getProjectAnalysisGroupSamplesByGuid(state, ownProps),
  analysisGroupsByGuid: getProjectAnalysisGroupsByGuid(state),
})

export { ProjectOverview as ProjectOverviewComponent }

export default connect(mapStateToProps)(ProjectOverview)
