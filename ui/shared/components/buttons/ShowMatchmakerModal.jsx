import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Header, Icon, List } from 'semantic-ui-react'

import { loadGenes } from 'redux/rootReducer'
import {
  getProjectsByGuid,
  getMatchmakerSubmissions,
  getMatchmakerMatchesLoading,
  getGenesById,
  getGenesIsLoading,
} from 'redux/selectors'
import { loadMmeMatches } from 'pages/Project/reducers'
import Modal from '../modal/Modal'
import SortableTable from '../table/SortableTable'
import DataLoader from '../DataLoader'
import ButtonLink from './ButtonLink'


const MME_FIELDS = [
  {
    name: 'contacted',
    width: 2,
    content: 'Contacted',
    textAlign: 'center',
    verticalAlign: 'top',
    format: val => <Icon name={val.contacted ? 'check' : 'x'} color={val.contacted ? 'green' : 'red'} />,
  },
  {
    name: 'geneIds',
    width: 3,
    content: 'Genes',
    verticalAlign: 'top',
  },
  {
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
  {
    name: 'comments',
    width: 5,
    content: 'Comments',
    verticalAlign: 'top',
  },
]

const BaseMatchmakerMatches = ({ matches, project, family, genesById, loading, load }) => {
  if (!matches) {
    return null
  }

  const geneIds = new Set()
  const matchResults = Object.values(matches.match_results).reduce(
    (acc, resultSummary) => [...acc, ...resultSummary.result.results], [],
  ).map((result) => {
    const analysisStatus = matches.result_analysis_state[result.patient.id] || {}
    return {
      id: result.patient.id,
      contacted: analysisStatus.host_contacted_us || analysisStatus.we_contacted_host,
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
        feature => ({ ...matches.hpo_map[feature.id], ...feature }),
      ),
      comments: analysisStatus.comments,
    }
  })

  return (
    <div>
      <a target="_blank" href={`/matchmaker/search/project/${project.deprecatedProjectId}/family/${family.familyId}`}>
        View Detailed Results
      </a>
      {/* TODO search in monarch */}
      <DataLoader contentId={geneIds} content loading={loading} load={load}>
        <SortableTable
          basic="very"
          fixed
          idField="id"
          defaultSortColumn="geneIds"
          columns={MME_FIELDS}
          data={matchResults}
        />
      </DataLoader>
    </div>
  )
}

BaseMatchmakerMatches.propTypes = {
  matches: PropTypes.object,
  project: PropTypes.object,
  family: PropTypes.object,
  genesById: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const matchmakerMatchesMapStateToProps = state => ({
  genesById: getGenesById(state),
  loading: getGenesIsLoading(state),
})

const matchmakerMatchesMapDispatchToProps = {
  load: loadGenes,
}

const MatchmakerMatches = connect(matchmakerMatchesMapStateToProps, matchmakerMatchesMapDispatchToProps)(BaseMatchmakerMatches)


const ShowMatchmakerModal = ({ project, family, loading, load, matchmakerSubmissions }) =>
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
        <DataLoader contentId={submission.individualId} content={submission.match} loading={loading} load={load}>
          <MatchmakerMatches matches={submission.match} project={project} family={family} />
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
}

const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[ownProps.family.projectGuid],
  matchmakerSubmissions: getMatchmakerSubmissions(state)[ownProps.family.projectGuid],
  loading: getMatchmakerMatchesLoading(state),
})

const mapDispatchToProps = {
  load: loadMmeMatches,
}

export default connect(mapStateToProps, mapDispatchToProps)(ShowMatchmakerModal)
