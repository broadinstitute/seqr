import React from 'react'
import PropTypes from 'prop-types'
import sortBy from 'lodash/sortBy'
import styled from 'styled-components'
import { Grid, Icon, Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'

import { getUser } from 'redux/selectors'
import { VerticalSpacer } from 'shared/components/Spacers'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import Modal from 'shared/components/modal/Modal'
import DataTable from 'shared/components/table/DataTable'
import { ButtonLink, HelpIcon } from 'shared/components/StyledComponents'
import {
  SAMPLE_TYPE_LOOKUP,
  GENOME_VERSION_LOOKUP,
  DATASET_TYPE_SV_CALLS,
  ANVIL_URL,
} from 'shared/utils/constants'
import {
  getAnalysisStatusCounts,
  getProjectAnalysisGroupFamiliesByGuid,
  getProjectAnalysisGroupIndividualsCount,
  getProjectAnalysisGroupSamplesByTypes,
  getProjectAnalysisGroupMmeSubmissions,
  getProjectAnalysisGroupMmeSubmissionDetails,
} from '../selectors'
import EditFamiliesAndIndividualsButton from './edit-families-and-individuals/EditFamiliesAndIndividualsButton'
import EditIndividualMetadataButton from './edit-families-and-individuals/EditIndividualMetadataButton'
import EditDatasetsButton from './EditDatasetsButton'

const DetailContent = styled.div`
 padding: 5px 0px 0px 20px;
`

const DATASET_TITLE_LOOKUP = { [DATASET_TYPE_SV_CALLS]: ' SV' }

const FAMILY_SIZE_LABELS = {
  0: plural => ` ${plural ? 'families' : 'family'} with no individuals`,
  1: plural => ` ${plural ? 'families' : 'family'} with 1 individual`,
  2: plural => ` ${plural ? 'families' : 'family'} with 2 individuals`,
  3: plural => ` trio${plural ? 's' : ''}`,
  4: plural => ` quad${plural ? 's' : ''}`,
  5: plural => ` ${plural ? 'families' : 'family'} with 5+ individuals`,
}

const DetailSection = React.memo(({ title, content, button }) => (
  <div>
    <b>{title}</b>
    <DetailContent>{content}</DetailContent>
    {button && (
      <div>
        <VerticalSpacer height={15} />
        {button}
      </div>
    )}
  </div>
))

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
    format: row => (
      <NavLink to={`/project/${row.projectGuid}/family_page/${row.familyGuid}/matchmaker_exchange`} target="_blank">
        <Icon name="linkify" link />
      </NavLink>
    ),
  },
  { name: 'familyName', content: 'Family', width: 2 },
  { name: 'geneSymbols', content: 'Genes', width: 3, format: ({ geneSymbols }) => (geneSymbols || []).join(', ') },
  { name: 'createdDate', content: 'Created Date', width: 2, format: ({ createdDate }) => createdDate && new Date(createdDate).toLocaleDateString() },
  { name: 'deletedDate', content: 'Removed Date', width: 2, format: ({ deletedDate }) => deletedDate && new Date(deletedDate).toLocaleDateString() },
  { name: 'mmeNotes', content: 'Notes', width: 6, format: ({ mmeNotes }) => (mmeNotes || []).map(({ note }) => note).join('; ') },
]

const BaseMatchmakerSubmissionOverview = React.memo(({ mmeSubmissions }) => (
  <DataTable
    basic="very"
    fixed
    data={Object.values(mmeSubmissions)}
    idField="submissionGuid"
    defaultSortColumn="familyName"
    columns={MME_COLUMNS}
  />
))

BaseMatchmakerSubmissionOverview.propTypes = {
  mmeSubmissions: PropTypes.arrayOf(PropTypes.object),
}

const mapMatchmakerSubmissionsStateToProps = (state, ownProps) => ({
  mmeSubmissions: getProjectAnalysisGroupMmeSubmissionDetails(state, ownProps),
})

const MatchmakerSubmissionOverview = connect(mapMatchmakerSubmissionsStateToProps)(BaseMatchmakerSubmissionOverview)

const FamiliesIndividuals = React.memo(({ project, familiesByGuid, individualsCount, user }) => {
  const familySizeHistogram = Object.values(familiesByGuid)
    .map(family => Math.min(family.individualGuids.length, 5))
    .reduce((acc, familySize) => (
      { ...acc, [familySize]: (acc[familySize] || 0) + 1 }
    ), {})

  let editIndividualsButton = null
  if (user.isPm || (project.hasCaseReview && project.canEdit)) {
    editIndividualsButton = <EditFamiliesAndIndividualsButton />
  } else if (project.canEdit) {
    editIndividualsButton = <EditIndividualMetadataButton />
  }

  return (
    <DetailSection
      title={`${Object.keys(familiesByGuid).length} Families, ${individualsCount} Individuals`}
      content={
        sortBy(Object.keys(familySizeHistogram)).map(size => (
          <div key={size}>{`${familySizeHistogram[size]} ${FAMILY_SIZE_LABELS[size](familySizeHistogram[size] > 1)}`}</div>
        ))
      }
      button={editIndividualsButton}
    />
  )
})

FamiliesIndividuals.propTypes = {
  project: PropTypes.object.isRequired,
  familiesByGuid: PropTypes.object.isRequired,
  individualsCount: PropTypes.number,
  user: PropTypes.object.isRequired,
}

const mapFamiliesStateToProps = (state, ownProps) => ({
  user: getUser(state),
  familiesByGuid: getProjectAnalysisGroupFamiliesByGuid(state, ownProps),
  individualsCount: getProjectAnalysisGroupIndividualsCount(state, ownProps),
})

const FamiliesIndividualsOverview = connect(mapFamiliesStateToProps)(FamiliesIndividuals)

const Matchmaker = React.memo(({ project, mmeSubmissions }) => {
  const mmeSubmissionCount = mmeSubmissions.length
  const deletedSubmissionCount = mmeSubmissions.filter(({ deletedDate }) => deletedDate).length

  return (
    <DetailSection
      title="Matchmaker Submissions"
      content={mmeSubmissionCount ? (
        <div>
          {`${mmeSubmissionCount - deletedSubmissionCount} submissions `}
          <Modal
            trigger={<ButtonLink icon="external" size="tiny" />}
            title={`Matchmaker Submissions for ${project.name}`}
            modalName="mmeSubmissions"
            size="large"
          >
            <MatchmakerSubmissionOverview />
          </Modal>
          {deletedSubmissionCount > 0 && <div>{`${deletedSubmissionCount} removed submissions`}</div>}
        </div>
      ) : 'No Submissions'}
    />
  )
})

Matchmaker.propTypes = {
  project: PropTypes.object.isRequired,
  mmeSubmissions: PropTypes.arrayOf(PropTypes.object),
}

const mapMatchmakerStateToProps = (state, ownProps) => ({
  mmeSubmissions: getProjectAnalysisGroupMmeSubmissions(state, ownProps),
})

const MatchmakerOverview = connect(mapMatchmakerStateToProps)(Matchmaker)

class DatasetSection extends React.PureComponent {

  static propTypes = {
    loadedSampleCounts: PropTypes.object.isRequired,
  }

  state = { showAll: false }

  show = () => {
    this.setState({ showAll: true })
  }

  render() {
    const { loadedSampleCounts } = this.props
    const { showAll } = this.state
    const allLoads = Object.keys(loadedSampleCounts).sort().map(loadedDate => (
      <div key={loadedDate}>
        {`${new Date(loadedDate).toLocaleDateString()} - ${loadedSampleCounts[loadedDate]} samples`}
      </div>
    ))

    const total = allLoads.length
    if (total < 6 || showAll) {
      return allLoads
    }

    return [
      ...allLoads.slice(0, 2),
      <ButtonLink key="show" padding="5px 0" onClick={this.show}>{`Show ${total - 5} additional datasets`}</ButtonLink>,
      ...allLoads.slice(total - 3),
    ]
  }

}

const Dataset = React.memo(({ project, samplesByType, user }) => {
  const datasetSections = Object.entries(samplesByType).map(([sampleTypeKey, loadedSampleCounts]) => {
    const [sampleType, datasetType] = sampleTypeKey.split('__')
    return {
      key: sampleTypeKey,
      title: `${SAMPLE_TYPE_LOOKUP[sampleType].text}${DATASET_TITLE_LOOKUP[datasetType] || ''} Datasets`,
      content: <DatasetSection loadedSampleCounts={loadedSampleCounts} />,
    }
  }).sort((a, b) => a.title.localeCompare(b.title))

  if (!datasetSections.length) {
    datasetSections.push({
      title: 'Datasets',
      content: (
        <div>
          No Datasets Loaded
          {project.workspaceName && (
            <div>
              <i>Where is my data? </i>
              <Popup
                trigger={<HelpIcon />}
                hoverable
                content={
                  <div>
                    Loading data from AnVIL to seqr is a slow process, and generally takes a week.
                    If you have been waiting longer than this for your data, please reach
                    out to &nbsp;
                    <a href="mailto:seqr@populationgenomics.org.au">seqr@populationgenomics.org.au</a>
                  </div>
                }
              />
            </div>
          )}
        </div>
      ),
      key: 'blank',
    })
  }

  return datasetSections.map((sectionProps, i) => (
    <DetailSection
      {...sectionProps}
      button={(datasetSections.length - 1 === i) ? <EditDatasetsButton user={user} /> : null}
    />
  ))
})

Dataset.propTypes = {
  project: PropTypes.object.isRequired,
  samplesByType: PropTypes.object.isRequired,
  user: PropTypes.object.isRequired,
}

const mapDatasetStateToProps = (state, ownProps) => ({
  user: getUser(state),
  samplesByType: getProjectAnalysisGroupSamplesByTypes(state, ownProps),
})

const DatasetOverview = connect(mapDatasetStateToProps)(Dataset)

const Anvil = React.memo(({ project, user }) => (
  project.workspaceName && user.isAnvil && (
    <DetailSection
      title="AnVIL Workspace"
      content={
        <a href={`${ANVIL_URL}/#workspaces/${project.workspaceNamespace}/${project.workspaceName}`} target="_blank" rel="noreferrer">
          {project.workspaceName}
        </a>
      }
    />
  )
))

Anvil.propTypes = {
  project: PropTypes.object.isRequired,
  user: PropTypes.object.isRequired,
}

const mapAnvilStateToProps = state => ({
  user: getUser(state),
})

const AnvilOverview = connect(mapAnvilStateToProps)(Anvil)

const AnalysisStatus = React.memo(({ analysisStatusCounts }) => (
  <DetailSection
    title="Analysis Status"
    content={<HorizontalStackedBar height={20} title="Analysis Statuses" data={analysisStatusCounts} />}
  />
))

AnalysisStatus.propTypes = {
  analysisStatusCounts: PropTypes.arrayOf(PropTypes.object).isRequired,
}

const mapAnalysisStatusStateToProps = (state, ownProps) => ({
  analysisStatusCounts: getAnalysisStatusCounts(state, ownProps),
})

const AnalysisStatusOverview = connect(mapAnalysisStatusStateToProps)(AnalysisStatus)

const ProjectOverview = React.memo(props => (
  <Grid>
    <Grid.Column width={5}>
      <FamiliesIndividualsOverview {...props} />
      <VerticalSpacer height={10} />
      <MatchmakerOverview {...props} />
    </Grid.Column>
    <Grid.Column width={5}>
      <DetailSection title="Genome Version" content={GENOME_VERSION_LOOKUP[props.project.genomeVersion]} />
      <DatasetOverview {...props} />
    </Grid.Column>
    <Grid.Column width={6}>
      <AnvilOverview {...props} />
      <AnalysisStatusOverview {...props} />
    </Grid.Column>
  </Grid>
))

ProjectOverview.propTypes = {
  project: PropTypes.object.isRequired,
}

export default ProjectOverview
