import React from 'react'
import PropTypes from 'prop-types'
import sortBy from 'lodash/sortBy'
import styled from 'styled-components'
import { Grid, Icon, Popup, Loader, Dimmer } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'

import { getUser, getElasticsearchEnabled } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { VerticalSpacer } from 'shared/components/Spacers'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import { validators } from 'shared/components/form/FormHelpers'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import Modal from 'shared/components/modal/Modal'
import DataTable from 'shared/components/table/DataTable'
import { ButtonLink, HelpIcon } from 'shared/components/StyledComponents'
import {
  SAMPLE_TYPE_LOOKUP,
  GENOME_VERSION_LOOKUP,
  DATASET_TITLE_LOOKUP,
  ANVIL_URL,
  ANVIL_FIELDS,
} from 'shared/utils/constants'
import { updateProjectMmeContact, loadMmeSubmissions, updateAnvilWorkspace } from '../reducers'
import {
  getCurrentProject,
  getAnalysisStatusCounts,
  getProjectAnalysisGroupFamilyIndividualCounts,
  getProjectAnalysisGroupDataLoadedFamilyIndividualCounts,
  getProjectAnalysisGroupSamplesByTypes,
  getProjectAnalysisGroupMmeSubmissionDetails,
  getMmeSubmissionsLoading,
} from '../selectors'
import EditFamiliesAndIndividualsButton from './edit-families-and-individuals/EditFamiliesAndIndividualsButton'
import EditIndividualMetadataButton from './edit-families-and-individuals/EditIndividualMetadataButton'
import EditDatasetsButton from './EditDatasetsButton'

const DetailContent = styled.div`
 padding: 5px 0px 0px 20px;
`

const FAMILY_SIZE_LABELS = {
  0: 'no',
  5: '5+',
}

const FAMILY_STRUCTURE_SIZE_LABELS = {
  2: plural => ` duo${plural ? 's' : ''}`,
  3: plural => ` trio${plural ? 's' : ''}`,
  4: plural => ` quad${plural ? 's' : ''}`,
  5: plural => ` trio${plural ? 's' : ''}+`,
}

const FAMILY_STRUCTURE_HOVER = {
  2: 'A family with one parent and one child',
  3: 'A family with two parents and one child',
  4: 'A family with two parents and two children',
  5: 'A family with two parents and three or more other family members',
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
  title: PropTypes.node.isRequired,
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

const MME_CONTACT_FIELDS = [
  {
    name: 'contact',
    label: 'Contact Email',
    validate: validators.requiredEmail,
  },
]

const BaseMatchmakerSubmissionOverview = React.memo(({ canEdit, mmeSubmissions, onSubmit, load, loading }) => (
  <DataLoader load={load} loading={false} content>
    {canEdit && (
      <UpdateButton
        onSubmit={onSubmit}
        buttonText="Add Contact to MME Submissions"
        editIconName="plus"
        buttonFloated="right"
        modalTitle="Add Contact to MME Submissions"
        modalId="mmeContact"
        formFields={MME_CONTACT_FIELDS}
        confirmDialog="Are you sure you want to add this contact to all MME submissions in this project?"
        showErrorPanel
      />
    )}
    <DataTable
      basic="very"
      fixed
      loading={loading}
      data={Object.values(mmeSubmissions)}
      idField="submissionGuid"
      defaultSortColumn="familyName"
      columns={MME_COLUMNS}
    />
  </DataLoader>
))

BaseMatchmakerSubmissionOverview.propTypes = {
  mmeSubmissions: PropTypes.arrayOf(PropTypes.object),
  loading: PropTypes.bool,
  load: PropTypes.func,
  canEdit: PropTypes.bool,
  onSubmit: PropTypes.func,
}

const mapMatchmakerSubmissionsStateToProps = (state, ownProps) => ({
  mmeSubmissions: getProjectAnalysisGroupMmeSubmissionDetails(state, ownProps),
  loading: getMmeSubmissionsLoading(state),
})

const mapDispatchToProps = {
  load: loadMmeSubmissions,
  onSubmit: updateProjectMmeContact,
}

const MatchmakerSubmissionOverview = connect(
  mapMatchmakerSubmissionsStateToProps, mapDispatchToProps,
)(BaseMatchmakerSubmissionOverview)

const FamiliesIndividuals = React.memo(({ canEdit, hasCaseReview, familyCounts, user, title }) => {
  const familySizeHistogram = familyCounts.reduce((acc, { size, numParents }) => {
    const familySize = Math.min(size, 5)
    const sizeAcc = acc[familySize] || { total: 0, withParents: 0 }
    sizeAcc.total += 1
    if (familySize === 2 && numParents) {
      sizeAcc.withParents += 1
    } else if (familySize > 2 && numParents === 2) {
      sizeAcc.withParents += 1
    }
    return { ...acc, [familySize]: sizeAcc }
  }, {})
  const individualsCount = familyCounts.reduce((acc, { size }) => acc + size, 0)

  let editIndividualsButton = null
  if (user && (user.isPm || (hasCaseReview && canEdit))) {
    editIndividualsButton = <EditFamiliesAndIndividualsButton />
  } else if (user && canEdit) {
    editIndividualsButton = <EditIndividualMetadataButton />
  }

  return (
    <DetailSection
      title={(
        <span>
          {`${Object.keys(familyCounts).length} Families${title || ''},`}
          <br />
          {`${individualsCount} Individuals${title || ''}`}
        </span>
      )}
      content={
        sortBy(Object.entries(familySizeHistogram)).map(([size, { total, withParents }]) => (
          <div key={size}>
            {`${total} famil${total === 1 ? 'y' : 'ies'} with ${FAMILY_SIZE_LABELS[size] || size} individual${size === '1' ? '' : 's'}`}
            {withParents > 0 && (
              <div>
                &nbsp;&nbsp;&nbsp;&nbsp;
                {withParents}
                <Popup
                  trigger={<span>{FAMILY_STRUCTURE_SIZE_LABELS[size](total > 1)}</span>}
                  content={FAMILY_STRUCTURE_HOVER[size]}
                />
              </div>
            )}
          </div>
        ))
      }
      button={editIndividualsButton}
    />
  )
})

FamiliesIndividuals.propTypes = {
  familyCounts: PropTypes.arrayOf(PropTypes.object).isRequired,
  canEdit: PropTypes.bool,
  hasCaseReview: PropTypes.bool,
  user: PropTypes.object,
  title: PropTypes.string,
}

const mapFamiliesStateToProps = (state, ownProps) => ({
  user: getUser(state),
  familyCounts: getProjectAnalysisGroupFamilyIndividualCounts(state, ownProps),
})

const mapDataLoadedFamiliesStateToProps = (state, ownProps) => ({
  title: ' With Data',
  familyCounts: getProjectAnalysisGroupDataLoadedFamilyIndividualCounts(state, ownProps),
})

const FamiliesIndividualsOverview = connect(mapFamiliesStateToProps)(FamiliesIndividuals)

const DataLoadedFamiliesIndividualsOverview = connect(mapDataLoadedFamiliesStateToProps)(FamiliesIndividuals)

const MatchmakerOverview = React.memo(({ projectName, mmeSubmissionCount, mmeDeletedSubmissionCount, canEdit }) => (
  <DetailSection
    title="Matchmaker Submissions"
    content={mmeSubmissionCount ? (
      <div>
        {`${mmeSubmissionCount} submissions `}
        <Modal
          trigger={<ButtonLink icon="external" size="tiny" />}
          title={`Matchmaker Submissions for ${projectName}`}
          modalName="mmeSubmissions"
          size="large"
        >
          <MatchmakerSubmissionOverview canEdit={canEdit} />
        </Modal>
        {mmeDeletedSubmissionCount > 0 && <div>{`${mmeDeletedSubmissionCount} removed submissions`}</div>}
      </div>
    ) : 'No Submissions'}
  />
))

MatchmakerOverview.propTypes = {
  projectName: PropTypes.string.isRequired,
  canEdit: PropTypes.bool,
  mmeSubmissionCount: PropTypes.number,
  mmeDeletedSubmissionCount: PropTypes.number,
}

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

const Dataset = React.memo(({ showLoadWorkspaceData, hasAnvil, samplesByType, user, elasticsearchEnabled }) => {
  const datasetSections = Object.entries(samplesByType).map(([sampleTypeKey, loadedSampleCounts]) => {
    const [sampleType, datasetType] = sampleTypeKey.split('__')
    return {
      key: sampleTypeKey,
      title: `${SAMPLE_TYPE_LOOKUP[sampleType].text}${DATASET_TITLE_LOOKUP[datasetType] || ''} Datasets`,
      content: <DatasetSection loadedSampleCounts={loadedSampleCounts} />,
    }
  }).sort((a, b) => a.title.localeCompare(b.title))

  const noLoadedData = !datasetSections.length
  if (noLoadedData) {
    datasetSections.push({
      title: 'Datasets',
      content: (
        <div>
          No Datasets Loaded
          {hasAnvil && (
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
                    <a href="mailto:seqr@broadinstitute.org">seqr@broadinstitute.org</a>
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
      button={(datasetSections.length - 1 === i) ? (
        <EditDatasetsButton
          showLoadWorkspaceData={showLoadWorkspaceData && !noLoadedData}
          user={user}
          elasticsearchEnabled={elasticsearchEnabled}
        />
      ) : null}
    />
  ))
})

Dataset.propTypes = {
  samplesByType: PropTypes.object.isRequired,
  hasAnvil: PropTypes.bool,
  showLoadWorkspaceData: PropTypes.bool,
  elasticsearchEnabled: PropTypes.bool,
  user: PropTypes.object.isRequired,
}

const mapDatasetStateToProps = (state, ownProps) => ({
  user: getUser(state),
  elasticsearchEnabled: getElasticsearchEnabled(state),
  samplesByType: getProjectAnalysisGroupSamplesByTypes(state, ownProps),
})

const DatasetOverview = connect(mapDatasetStateToProps)(Dataset)

const mapAnvilButtonStateToProps = state => ({
  initialValues: getCurrentProject(state),
})

const UpdateAnvilButton = connect(mapAnvilButtonStateToProps)(UpdateButton)

const Anvil = React.memo(({ workspaceName, workspaceNamespace, user, onSubmit }) => (
  (workspaceName || user.isPm) && user.isAnvil && (
    <DetailSection
      title="AnVIL Workspace"
      content={workspaceName ? (
        <a href={`${ANVIL_URL}/#workspaces/${workspaceNamespace}/${workspaceName}`} target="_blank" rel="noreferrer">
          {workspaceName}
        </a>
      ) : 'None'}
      button={user.isPm && (
        <UpdateAnvilButton
          onSubmit={onSubmit}
          formFields={ANVIL_FIELDS}
          modalTitle="Edit AnVIL Workspace"
          modalId="editAnvilWorkspace"
          buttonText="Edit Workspace"
        />
      )}
    />
  )
))

Anvil.propTypes = {
  user: PropTypes.object.isRequired,
  workspaceName: PropTypes.string,
  workspaceNamespace: PropTypes.string,
  onSubmit: PropTypes.func,
}

const mapAnvilStateToProps = state => ({
  user: getUser(state),
})

const mapAnvilDispatchToProps = {
  onSubmit: updateAnvilWorkspace,
}

const AnvilOverview = connect(mapAnvilStateToProps, mapAnvilDispatchToProps)(Anvil)

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

const LoadingSection = ({ loading, children }) => (
  loading ? <Dimmer inverted active><Loader /></Dimmer> : children
)

LoadingSection.propTypes = {
  loading: PropTypes.bool,
  children: PropTypes.node,
}

const ProjectOverview = React.memo(({
  familiesLoading, overviewLoading, analysisGroupGuid, projectName, genomeVersion, workspaceName, workspaceNamespace,
  canEdit, hasCaseReview, isAnalystProject, mmeSubmissionCount, mmeDeletedSubmissionCount,
}) => (
  <Grid>
    <Grid.Column width={5}>
      <LoadingSection loading={familiesLoading}>
        <FamiliesIndividualsOverview
          canEdit={canEdit}
          hasCaseReview={hasCaseReview}
          analysisGroupGuid={analysisGroupGuid}
        />
      </LoadingSection>
      <VerticalSpacer height={10} />
      <LoadingSection loading={familiesLoading || overviewLoading}>
        <DataLoadedFamiliesIndividualsOverview
          canEdit={canEdit}
          hasCaseReview={hasCaseReview}
          analysisGroupGuid={analysisGroupGuid}
        />
      </LoadingSection>
      <VerticalSpacer height={10} />
      <LoadingSection loading={overviewLoading}>
        <MatchmakerOverview
          projectName={projectName}
          mmeSubmissionCount={mmeSubmissionCount}
          mmeDeletedSubmissionCount={mmeDeletedSubmissionCount}
          canEdit={canEdit}
        />
      </LoadingSection>
    </Grid.Column>
    <Grid.Column width={5}>
      <DetailSection title="Genome Version" content={GENOME_VERSION_LOOKUP[genomeVersion]} />
      <LoadingSection loading={overviewLoading}>
        <DatasetOverview
          showLoadWorkspaceData={!!workspaceName && !isAnalystProject && canEdit}
          hasAnvil={!!workspaceName}
          analysisGroupGuid={analysisGroupGuid}
        />
      </LoadingSection>
    </Grid.Column>
    <Grid.Column width={6}>
      <LoadingSection loading={familiesLoading}>
        <AnalysisStatusOverview analysisGroupGuid={analysisGroupGuid} />
      </LoadingSection>
      <VerticalSpacer height={10} />
      <AnvilOverview workspaceName={workspaceName} workspaceNamespace={workspaceNamespace} />
    </Grid.Column>
  </Grid>
))

ProjectOverview.propTypes = {
  projectName: PropTypes.string,
  genomeVersion: PropTypes.string,
  workspaceName: PropTypes.string,
  workspaceNamespace: PropTypes.string,
  canEdit: PropTypes.bool,
  hasCaseReview: PropTypes.bool,
  isAnalystProject: PropTypes.bool,
  mmeSubmissionCount: PropTypes.number,
  mmeDeletedSubmissionCount: PropTypes.number,
  analysisGroupGuid: PropTypes.string,
  familiesLoading: PropTypes.bool,
  overviewLoading: PropTypes.bool,
}

const mapStateToProps = (state) => {
  const {
    name,
    genomeVersion,
    workspaceName,
    workspaceNamespace,
    canEdit,
    hasCaseReview,
    isAnalystProject,
    mmeSubmissionCount,
    mmeDeletedSubmissionCount,
  } = getCurrentProject(state)
  return {
    projectName: name,
    genomeVersion,
    workspaceName,
    workspaceNamespace,
    canEdit,
    hasCaseReview,
    isAnalystProject,
    mmeSubmissionCount,
    mmeDeletedSubmissionCount,
  }
}

export default connect(mapStateToProps)(ProjectOverview)
