import React from 'react'
import PropTypes from 'prop-types'
import sortBy from 'lodash/sortBy'
import styled from 'styled-components'
import { Grid, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'

import { getUser } from 'redux/selectors'
import { VerticalSpacer, HorizontalSpacer } from 'shared/components/Spacers'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import Modal from 'shared/components/modal/Modal'
import DataTable from 'shared/components/table/DataTable'
import { ButtonLink } from 'shared/components/StyledComponents'
import {
  SAMPLE_TYPE_LOOKUP,
  DATASET_TYPE_VARIANT_CALLS,
  GENOME_VERSION_LOOKUP,
} from 'shared/utils/constants'
import {
  getAnalysisStatusCounts,
  getProjectAnalysisGroupFamiliesByGuid,
  getProjectAnalysisGroupIndividualsByGuid,
  getProjectAnalysisGroupSamplesByGuid,
  getProjectAnalysisGroupMmeSubmissions,
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

const DetailSection = React.memo(({ title, content, button }) =>
  <div>
    <b>{title}</b>
    <DetailContent>{content}</DetailContent>
    {button && <div><VerticalSpacer height={15} />{button}</div>}
  </div>,
)

DetailSection.propTypes = {
  title: PropTypes.string.isRequired,
  content: PropTypes.node.isRequired,
  button: PropTypes.node,
}

const MME_COLUMNS = [
  {
    name: 'href',
    content: '',
    width: 1,
    format: row =>
      <NavLink to={`/project/${row.projectGuid}/family_page/${row.familyGuid}/matchmaker_exchange`} target="_blank">
        <Icon name="linkify" link />
      </NavLink>,
  },
  { name: 'familyName', content: 'Family', width: 2 },
  { name: 'individualName', content: 'Individual', width: 2 },
  { name: 'createdDate', content: 'Created Date', width: 2, format: ({ createdDate }) => createdDate && new Date(createdDate).toLocaleDateString() },
  { name: 'deletedDate', content: 'Removed Date', width: 2, format: ({ deletedDate }) => deletedDate && new Date(deletedDate).toLocaleDateString() },
  { name: 'mmeNotes', content: 'Notes', width: 7 },
]

const MatchmakerSubmissionOverview = React.memo(({ mmeSubmissions }) => {
  return (
    <DataTable
      basic="very"
      fixed
      data={Object.values(mmeSubmissions)}
      idField="submissionGuid"
      defaultSortColumn="familyName"
      columns={MME_COLUMNS}
    />
  )
})

MatchmakerSubmissionOverview.propTypes = {
  mmeSubmissions: PropTypes.array,
}

const ProjectOverview = React.memo((
  { project, familiesByGuid, individualsByGuid, samplesByGuid, mmeSubmissions, analysisStatusCounts, user },
) => {
  const familySizeHistogram = Object.values(familiesByGuid)
    .map(family => Math.min(family.individualGuids.length, 5))
    .reduce((acc, familySize) => (
      { ...acc, [familySize]: (acc[familySize] || 0) + 1 }
    ), {})

  const loadedProjectSamples = Object.values(samplesByGuid).filter(sample =>
    sample.datasetType === DATASET_TYPE_VARIANT_CALLS,
  ).reduce((acc, sample) => {
    const loadedDate = (sample.loadedDate || '').split('T')[0]
    const currentTypeSamplesByDate = acc[sample.sampleType] || {}
    return { ...acc, [sample.sampleType]: { ...currentTypeSamplesByDate, [loadedDate]: (currentTypeSamplesByDate[loadedDate] || 0) + 1 } }
  }, {})

  let editIndividualsButton = null
  if (user.isStaff) {
    editIndividualsButton = <EditFamiliesAndIndividualsButton />
  } else if (project.canEdit) {
    editIndividualsButton = <EditHpoTermsButton />
  }

  const mmeSubmissionCount = mmeSubmissions.length
  const deletedSubmissionCount = mmeSubmissions.filter(({ deletedDate }) => deletedDate).length

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
        <VerticalSpacer height={10} />
        <DetailSection
          title="Matchmaker Submissions"
          content={mmeSubmissionCount ?
            <div>
              {mmeSubmissionCount - deletedSubmissionCount} submissions <HorizontalSpacer width={5} />
              <Modal
                trigger={<ButtonLink icon="external" size="tiny" />}
                title={`Matchmaker Submissions for ${project.name}`}
                modalName="mmeSubmissions"
                size="large"
              >
                <MatchmakerSubmissionOverview mmeSubmissions={mmeSubmissions} />
              </Modal>
              {deletedSubmissionCount > 0 && <div>{deletedSubmissionCount} removed submissions</div>}
            </div>
            : 'No Submissions'
          }
        />
      </Grid.Column>
      <Grid.Column width={5}>
        <DetailSection title="Genome Version" content={GENOME_VERSION_LOOKUP[project.genomeVersion]} />
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
})


ProjectOverview.propTypes = {
  project: PropTypes.object.isRequired,
  familiesByGuid: PropTypes.object.isRequired,
  individualsByGuid: PropTypes.object.isRequired,
  samplesByGuid: PropTypes.object.isRequired,
  mmeSubmissions: PropTypes.array,
  analysisStatusCounts: PropTypes.array.isRequired,
  user: PropTypes.object.isRequired,
}

const mapStateToProps = (state, ownProps) => ({
  user: getUser(state),
  familiesByGuid: getProjectAnalysisGroupFamiliesByGuid(state, ownProps),
  individualsByGuid: getProjectAnalysisGroupIndividualsByGuid(state, ownProps),
  samplesByGuid: getProjectAnalysisGroupSamplesByGuid(state, ownProps),
  analysisStatusCounts: getAnalysisStatusCounts(state, ownProps),
  mmeSubmissions: getProjectAnalysisGroupMmeSubmissions(state, ownProps),
})

export default connect(mapStateToProps)(ProjectOverview)
