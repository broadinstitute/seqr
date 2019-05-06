import React from 'react'
import PropTypes from 'prop-types'
import sortBy from 'lodash/sortBy'
import styled from 'styled-components'
import { Grid } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { getUser } from 'redux/selectors'
import { VerticalSpacer } from 'shared/components/Spacers'
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
import EditFamiliesAndIndividualsButton from './edit-families-and-individuals/EditFamiliesAndIndividualsButton'
import EditHpoTermsButton from './edit-families-and-individuals/EditHpoTermsButton'
import EditDatasetsButton from './EditDatasetsButton'


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

const DetailSection = ({ title, content, button }) =>
  <div>
    <b>{title}</b>
    <DetailContent>{content}</DetailContent>
    {button && <div><VerticalSpacer height={15} />{button}</div>}
  </div>

DetailSection.propTypes = {
  title: PropTypes.string.isRequired,
  content: PropTypes.node.isRequired,
  button: PropTypes.node,
}

const ProjectOverview = ({ project, familiesByGuid, individualsByGuid, samplesByGuid, analysisStatusCounts, user }) => {
  const familySizeHistogram = Object.values(familiesByGuid)
    .map(family => Math.min(family.individualGuids.length, 5))
    .reduce((acc, familySize) => (
      { ...acc, [familySize]: (acc[familySize] || 0) + 1 }
    ), {})

  const loadedProjectSamples = Object.values(samplesByGuid).filter(sample =>
    sample.datasetType === DATASET_TYPE_VARIANT_CALLS && sample.sampleStatus === SAMPLE_STATUS_LOADED,
  ).reduce((acc, sample) => {
    const loadedDate = sample.loadedDate.split('T')[0]
    const currentTypeSamplesByDate = acc[sample.sampleType] || {}
    return { ...acc, [sample.sampleType]: { ...currentTypeSamplesByDate, [loadedDate]: (currentTypeSamplesByDate[loadedDate] || 0) + 1 } }
  }, {})

  let editIndividualsButton = null
  if (user.isStaff) {
    editIndividualsButton = <EditFamiliesAndIndividualsButton />
  } else if (project.canEdit) {
    editIndividualsButton = <EditHpoTermsButton />
  }

  return (
    <Grid>
      <Grid.Column width={5}>
        <DetailSection
          title={`${Object.keys(familiesByGuid).length} Families, ${Object.keys(individualsByGuid).length} Individuals`}
          content={
            sortBy(Object.keys(familySizeHistogram)).map(size =>
              <div key={size}>
                {familySizeHistogram[size]} {FAMILY_SIZE_LABELS[size](familySizeHistogram[size] > 1)}
              </div>)
          }
          button={editIndividualsButton}
        />
      </Grid.Column>
      <Grid.Column width={5}>
        {Object.keys(loadedProjectSamples).length > 0 ?
          Object.keys(loadedProjectSamples).sort().map((sampleType, i) => (
            <DetailSection
              key={sampleType}
              title={`${SAMPLE_TYPE_LOOKUP[sampleType].text} Datasets`}
              content={
                Object.keys(loadedProjectSamples[sampleType]).sort().map(loadedDate =>
                  <div key={loadedDate}>
                    { new Date(loadedDate).toLocaleDateString()} - {loadedProjectSamples[sampleType][loadedDate]} samples
                  </div>,
                )
              }
              button={(Object.keys(loadedProjectSamples).length - 1 === i && project.canEdit) ? <EditDatasetsButton /> : null}
            />
          )) : <DetailSection title="Datasets" content="No Datasets Loaded" button={project.canEdit ? <EditDatasetsButton /> : null} />
        }
      </Grid.Column>
      <Grid.Column width={6}>
        <DetailSection
          title="Analysis Status"
          content={<HorizontalStackedBar height={20} title="Analysis Statuses" data={analysisStatusCounts} />}
        />
      </Grid.Column>
    </Grid>
  )
}


ProjectOverview.propTypes = {
  project: PropTypes.object.isRequired,
  familiesByGuid: PropTypes.object.isRequired,
  individualsByGuid: PropTypes.object.isRequired,
  samplesByGuid: PropTypes.object.isRequired,
  analysisStatusCounts: PropTypes.array.isRequired,
  user: PropTypes.object.isRequired,
}

const mapStateToProps = (state, ownProps) => ({
  user: getUser(state),
  familiesByGuid: getProjectAnalysisGroupFamiliesByGuid(state, ownProps),
  individualsByGuid: getProjectAnalysisGroupIndividualsByGuid(state, ownProps),
  samplesByGuid: getProjectAnalysisGroupSamplesByGuid(state, ownProps),
  analysisStatusCounts: getAnalysisStatusCounts(state, ownProps),
})

export default connect(mapStateToProps)(ProjectOverview)
