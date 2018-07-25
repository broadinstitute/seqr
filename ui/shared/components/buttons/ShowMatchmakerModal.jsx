import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Header, Icon, List, Accordion } from 'semantic-ui-react'

import { loadGenes } from 'redux/rootReducer'
import {
  getProjectsByGuid,
  getMatchmakerSubmissions,
  getMatchmakerMatchesLoading,
  getMonarchMatchesLoading,
  getGenesById,
  getGenesIsLoading,
} from 'redux/selectors'
import { loadMmeMatches } from 'pages/Project/reducers'
import Modal from '../modal/Modal'
import SortableTable from '../table/SortableTable'
import DataLoader from '../DataLoader'
import { HorizontalSpacer } from '../Spacers'
import ButtonLink from './ButtonLink'


const MATCH_FIELDS = {
  contacted: {
    name: 'contacted',
    width: 2,
    content: 'Contacted',
    textAlign: 'center',
    verticalAlign: 'top',
    format: val => <Icon name={val.contacted ? 'check' : 'x'} color={val.contacted ? 'green' : 'red'} />,
  },
  comments: {
    name: 'comments',
    width: 5,
    content: 'Comments',
    verticalAlign: 'top',
  },
  description: {
    name: 'description',
    width: 3,
    content: 'External Description',
    verticalAlign: 'top',
  },
  id: {
    name: 'id',
    width: 3,
    content: 'External ID',
    verticalAlign: 'top',
    format: val => (val.id.match('OMIM') ?
      <a target="_blank" href={`https://www.omim.org/entry/${val.id.replace('OMIM:', '')}`}>{val.id}</a> : val.id),
  },
  geneIds: {
    name: 'geneIds',
    width: 3,
    content: 'Genes',
    verticalAlign: 'top',
  },
  score: {
    name: 'score',
    width: 1,
    content: 'Score',
    verticalAlign: 'top',
  },
  phenotypes: {
    name: 'phenotypes',
    width: 6,
    content: 'Phenotypes',
    verticalAlign: 'top',
    format: val =>
      <List bulleted>
        {val.phenotypes.map(phenotype =>
          <List.Item key={phenotype.id}>{phenotype.name} ({phenotype.id})</List.Item>,
        )}
      </List>,
  },
}

const DISPLAY_FIELDS = {
  mmeMatch: [
    MATCH_FIELDS.contacted,
    MATCH_FIELDS.comments,
    MATCH_FIELDS.geneIds,
    MATCH_FIELDS.phenotypes,
  ],
  monarchMatch: [
    MATCH_FIELDS.id,
    MATCH_FIELDS.description,
    MATCH_FIELDS.score,
    MATCH_FIELDS.geneIds,
    MATCH_FIELDS.phenotypes,
  ],
}


const BaseMatches = ({ matchKey, submission, genesById, loading, load }) => {
  if (!submission[matchKey]) {
    return null
  }

  const geneIds = new Set()
  const matchResults = Object.values(submission[matchKey].match_results).filter(
    resultSummary => resultSummary.status_code === 200,
  ).reduce((acc, resultSummary) => [...acc, ...resultSummary.result.results], [])
    .filter(result => result.patient.id)
    .map((result) => {
      const analysisStatus = (submission[matchKey].result_analysis_state || {})[result.patient.id] || {}
      return {
        id: result.patient.id,
        contacted: analysisStatus.host_contacted_us || analysisStatus.we_contacted_host,
        comments: analysisStatus.comments,
        description: result.patient.label,
        geneIds: (result.patient.genomicFeatures || []).map((geneFeature) => {
          let geneId = geneFeature.gene.id
          if (geneId.startsWith('ENSG')) {
            const gene = genesById[geneId]
            if (!gene) {
              geneIds.add(geneId)
            } else {
              geneId = gene.symbol
            }
          }
          return geneId
        }).sort().join(', '),
        phenotypes: (result.patient.features || []).filter(feature => feature.observed !== 'no').map(
          feature => ({ ...submission[matchKey].hpo_map[feature.id], ...feature }),
        ),
        score: result.score.patient,
      }
    })

  return (
    <DataLoader contentId={geneIds} content loading={loading} load={load}>
      <SortableTable
        basic="very"
        fixed
        idField="id"
        defaultSortColumn={matchKey === 'mmeMatch' ? 'geneIds' : 'id'}
        columns={DISPLAY_FIELDS[matchKey]}
        data={matchResults}
      />
    </DataLoader>
  )
}

BaseMatches.propTypes = {
  matchKey: PropTypes.string.isRequired,
  submission: PropTypes.object,
  genesById: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const matchesMapStateToProps = state => ({
  genesById: getGenesById(state),
  loading: getGenesIsLoading(state),
})

const matchesMapDispatchToProps = {
  load: loadGenes,
}

const Matches = connect(matchesMapStateToProps, matchesMapDispatchToProps)(BaseMatches)

const monarchDetailPanels = submission => [{
  title: { content: <b>Similar patients in the Monarch Initiative</b>, key: 'title' },
  content: { content: <Matches matchKey="monarchMatch" submission={submission} />, key: 'monarch' },
}]

const ShowMatchmakerModal = ({ project, family, loading, load, monarchLoading, loadMonarch, matchmakerSubmissions }) =>
  <Modal
    trigger={<ButtonLink>Match Maker Exchange</ButtonLink>}
    title={`${family.displayName}: Match Maker Exchange`}
    modalName={`mme-${family.familyGuid}`}
    size="large"
  >
    {matchmakerSubmissions ? Object.values(matchmakerSubmissions).filter(
      submission => submission.familyId === family.familyId,
    ).map(submission =>
      <div key={submission.individualId}>
        <Header size="medium" disabled content={submission.individualId} dividing />
        <DataLoader contentId={submission} content={submission.mmeMatch} loading={loading} load={load}>
          <a target="_blank" href={`/matchmaker/search/project/${submission.projectId}/family/${submission.familyId}`}>
            View Detailed Results
          </a>
          <HorizontalSpacer width={10} /> | <HorizontalSpacer width={10} />
          <ButtonLink key="search" onClick={loadMonarch(submission)}>Search in the Monarch Initiative</ButtonLink>
          <DataLoader content={submission.monarchMatch} loading={monarchLoading} hideError>
            <Accordion defaultActiveIndex={0} panels={monarchDetailPanels(submission)} />
          </DataLoader>
          <Matches matchKey="mmeMatch" submission={submission} />
        </DataLoader>
      </div>,
    ) : (
      <div>
        <Header
          size="small"
          content="No individuals from this family have been submitted"
          icon={<Icon name="warning sign" color="orange" />}
        />
        <a target="_blank" href={`/matchmaker/search/project/${project.deprecatedProjectId}/family/${family.familyId}`}>
          Submit to Match Maker Exchange
        </a>
      </div>
    )}
  </Modal>

ShowMatchmakerModal.propTypes = {
  matchmakerSubmissions: PropTypes.object,
  project: PropTypes.object,
  family: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
  monarchLoading: PropTypes.bool,
  loadMonarch: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[ownProps.family.projectGuid],
  matchmakerSubmissions: getMatchmakerSubmissions(state)[ownProps.family.projectGuid],
  loading: getMatchmakerMatchesLoading(state),
  monarchLoading: getMonarchMatchesLoading(state),
})

const mapDispatchToProps = (dispatch) => {
  return {
    load: (values) => {
      return dispatch(loadMmeMatches(values))
    },
    loadMonarch: submission => () => {
      return dispatch(loadMmeMatches(submission, 'monarch'))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(ShowMatchmakerModal)
