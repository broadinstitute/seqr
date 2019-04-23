import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Header, Icon, List, Accordion } from 'semantic-ui-react'
import styled from 'styled-components'

import {
  getProjectsByGuid,
  getFamilyMatchmakerSubmissions,
  getMatchmakerMatchesLoading,
  getMonarchMatchesLoading,
  getGenesById,
} from 'redux/selectors'
import { loadMmeMatches } from 'pages/Project/reducers'
import ShowGeneModal from './ShowGeneModal'
import Modal from '../modal/Modal'
import SortableTable from '../table/SortableTable'
import DataLoader from '../DataLoader'
import { HorizontalSpacer } from '../Spacers'
import { ButtonLink } from '../StyledComponents'

const PhenotypeListItem = styled(List.Item)`
  text-decoration: ${props => (props.observed === 'no' ? 'line-through' : 'none')};
`


const MATCH_FIELDS = {
  contacted: {
    name: 'contacted',
    width: 1,
    content: 'Contacted',
    textAlign: 'center',
    verticalAlign: 'top',
    format: val =>
      <Icon
        name={val.hostContacted || val.weContacted ? 'check' : 'x'}
        color={val.hostContacted || val.weContacted ? 'green' : 'red'}
      />,
  },
  irrelevent: {
    name: 'irrelevent',
    width: 1,
    content: 'Irrelevent',
    textAlign: 'center',
    verticalAlign: 'top',
    format: val =>
      <Icon
        name={val.irrelevent ? 'check' : 'x'}
        color={val.irrelevent ? 'green' : 'red'}
      />,
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
  geneVariants: {
    name: 'geneVariants',
    width: 3,
    content: 'Genes',
    verticalAlign: 'top',
    format: val =>
      <List>
        {Object.entries(val.geneVariants).map(([geneId, variants]) =>
          <List.Item key={geneId}>
            <ShowGeneModal gene={val.genesById[geneId]} modalId={val.id} />
            {variants.length > 0 &&
              <List.List>
                {variants.map(({ chrom, pos, ref, alt }) =>
                  <List.Item key={pos}>
                    {chrom}:{pos}{alt && <span> {ref}<Icon fitted name="angle right" />{alt}</span>}
                  </List.Item>,
                )}
              </List.List>
            }
          </List.Item>,
        )}
      </List>,
  },
  score: {
    name: 'score',
    width: 1,
    content: 'Score',
    verticalAlign: 'top',
  },
  phenotypes: {
    name: 'phenotypes',
    width: 5,
    content: 'Phenotypes',
    verticalAlign: 'top',
    format: val =>
      <List bulleted>
        {val.phenotypes.map(phenotype =>
          <PhenotypeListItem key={phenotype.id} observed={phenotype.observed}>
            {phenotype.name} ({phenotype.id})
          </PhenotypeListItem>,
        )}
      </List>,
  },
  seenOn: {
    name: 'seenOn',
    width: 1,
    content: 'First Seen',
    verticalAlign: 'top',
    format: val => new Date(val.seenOn).toLocaleDateString(),
  },
}

const DISPLAY_FIELDS = {
  mmeMatch: [
    // TODO match id/ hover patient details
    MATCH_FIELDS.seenOn,
    // TODO contact info (patient.contact)
    MATCH_FIELDS.contacted,
    MATCH_FIELDS.irrelevent,
    MATCH_FIELDS.comments,
    MATCH_FIELDS.geneVariants,
    MATCH_FIELDS.phenotypes,
  ],
  monarchMatch: [
    MATCH_FIELDS.id,
    MATCH_FIELDS.description,
    MATCH_FIELDS.score,
    MATCH_FIELDS.genes,
    MATCH_FIELDS.phenotypes,
  ],
}


const BaseMatches = ({ matchKey, submission, genesById }) => {
  if (!submission[matchKey]) {
    return null
  }

  const matchResults = Object.values(submission[matchKey]).filter(
    result => result.id,
  ).map(({ matchStatus, ...result }) => ({
    genesById,
    ...matchStatus,
    ...result,
  }))

  return (
    <SortableTable
      basic="very"
      fixed
      idField="id"
      defaultSortColumn={matchKey === 'mmeMatch' ? 'seenOn' : 'id'}
      defaultSortDescending={matchKey === 'mmeMatch'}
      columns={DISPLAY_FIELDS[matchKey]}
      data={matchResults}
    />
  )
}

BaseMatches.propTypes = {
  matchKey: PropTypes.string.isRequired,
  submission: PropTypes.object,
  genesById: PropTypes.object,
}

const matchesMapStateToProps = state => ({
  genesById: getGenesById(state),
})

const Matches = connect(matchesMapStateToProps)(BaseMatches)

const monarchDetailPanels = submission => [{
  title: { content: <b>Similar patients in the Monarch Initiative</b>, key: 'title' },
  content: { content: <Matches matchKey="monarchMatch" submission={submission} />, key: 'monarch' },
}]

const ShowMatchmakerModal = ({ project, family, loading, load, monarchLoading, loadMonarch, matchmakerSubmissions }) =>
  <Modal
    trigger={<ButtonLink>Match Maker Exchange</ButtonLink>}
    title={`${family.displayName}: Match Maker Exchange`}
    modalName={`mme-${family.familyGuid}`}
    size="fullscreen"
  >
    {matchmakerSubmissions.length ? matchmakerSubmissions.map(submission =>
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
  matchmakerSubmissions: PropTypes.array,
  project: PropTypes.object,
  family: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
  monarchLoading: PropTypes.bool,
  loadMonarch: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[ownProps.family.projectGuid],
  matchmakerSubmissions: getFamilyMatchmakerSubmissions(state, ownProps),
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

export { ShowMatchmakerModal as ShowMatchmakerModalComponent }
export default connect(mapStateToProps, mapDispatchToProps)(ShowMatchmakerModal)
