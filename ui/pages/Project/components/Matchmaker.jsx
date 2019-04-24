import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Header, Icon, List, Accordion, Popup, Label } from 'semantic-ui-react'
import styled from 'styled-components'

import { getFamiliesByGuid, getGenesById } from 'redux/selectors'
import ShowGeneModal from 'shared/components/buttons/ShowGeneModal'
import SortableTable from 'shared/components/table/SortableTable'
import DataLoader from 'shared/components/DataLoader'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { ButtonLink } from 'shared/components/StyledComponents'
import { camelcaseToTitlecase } from 'shared/utils/stringUtils'

import { loadMmeMatches } from '../reducers'
import { getFamilyMatchmakerSubmissions, getMatchmakerMatchesLoading, getMonarchMatchesLoading } from '../selectors'

const PhenotypeListItem = styled(List.Item)`
  text-decoration: ${props => (props.observed === 'no' ? 'line-through' : 'none')};
`

const BreakWordLink = styled.a`
  word-break: break-all;
`

const MatchContainer = styled.div`
  word-break: break-all;
`

const PATIENT_FIELDS = ['label', 'sex', 'ageOfOnset', 'inheritanceMode', 'species']

const contactedLabel = (val) => {
  if (val.hostContacted) {
    return 'Host Contacted Us'
  }
  return val.weContacted ? 'We Contacted Host' : 'Not Contacted'
}

const MATCH_FIELDS = {
  patient: {
    name: 'id',
    width: 2,
    content: 'Match',
    verticalAlign: 'top',
    format: (val) => {
      const patientFields = PATIENT_FIELDS.filter(k => val.patient[k])
      return patientFields.length ? <Popup
        header="Patient Details"
        trigger={<MatchContainer>{val.id} <Icon link name="info circle" /></MatchContainer>}
        content={patientFields.map(k => <div key={k}><b>{camelcaseToTitlecase(k)}:</b> {val.patient[k]}</div>)}
      /> : <MatchContainer>{val.id}</MatchContainer>
    },
  },
  contact: {
    name: 'contact',
    width: 3,
    content: 'Contact',
    verticalAlign: 'top',
    format: ({ patient }) => patient.contact &&
      <div>
        <div><b>{patient.contact.institution}</b></div>
        <div>{patient.contact.name}</div>
        <BreakWordLink href={patient.contact.href}>{patient.contact.href.replace('mailto:', '')}</BreakWordLink>
      </div>,
  },
  matchStatus: {
    name: 'comments',
    width: 4,
    content: 'Follow Up Status',
    verticalAlign: 'top',
    format: val =>
      <div>
        <Label horizontal content={contactedLabel(val)} color={val.hostContacted || val.weContacted ? 'green' : 'red'} />
        {val.flagForAnalysis && <Label horizontal content="Flag for Analysis" color="purple" />}
        {val.deemedIrrelevent && <Label horizontal content="Deemed Irrelevent" color="red" />}
        <p>{val.comments}</p>
        {/* TODO edit*/}
      </div>,
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
    width: 2,
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
    width: 4,
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
    MATCH_FIELDS.patient,
    MATCH_FIELDS.seenOn,
    MATCH_FIELDS.contact,
    MATCH_FIELDS.geneVariants,
    MATCH_FIELDS.phenotypes,
    MATCH_FIELDS.matchStatus,
  ],
  // TODO monarch
  monarchMatch: [
    MATCH_FIELDS.id,
    MATCH_FIELDS.description,
    MATCH_FIELDS.score,
    MATCH_FIELDS.genes,
    MATCH_FIELDS.phenotypes,
  ],
}

const BaseMatches = ({ matchKey, submission, genesById, loading }) => {
  const matchResults = Object.values(submission[matchKey] || {}).filter(
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
      loading={loading}
    />
  )
}

BaseMatches.propTypes = {
  matchKey: PropTypes.string.isRequired,
  submission: PropTypes.object,
  genesById: PropTypes.object,
  loading: PropTypes.bool,
}

const matchesMapStateToProps = state => ({
  genesById: getGenesById(state),
})

const Matches = connect(matchesMapStateToProps)(BaseMatches)

const monarchDetailPanels = submission => [{
  title: { content: <b>Similar patients in the Monarch Initiative</b>, key: 'title' },
  content: { content: <Matches matchKey="monarchMatch" submission={submission} />, key: 'monarch' },
}]

const Matchmaker = ({ family, loading, load, searchMme, monarchLoading, loadMonarch, matchmakerSubmissions }) => (
  matchmakerSubmissions.length ? matchmakerSubmissions.map(submission =>
    <div key={submission.individualId}>
      <Header size="medium" content={submission.individualId} dividing />
      {/* TODO show submission details/ update */}
      <DataLoader contentId={submission.individualId} content load={load} loading={false}>
        <ButtonLink disabled={!submission.mmeMatch} onClick={searchMme(submission.individualId)}>
          Search for New Matches
        </ButtonLink>
        <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
        <ButtonLink disabled={!submission.mmeMatch} onClick={loadMonarch(submission.individualId)}>
          Search in the Monarch Initiative
        </ButtonLink>
        <DataLoader content={submission.monarchMatch} loading={monarchLoading} hideError>
          <Accordion defaultActiveIndex={0} panels={monarchDetailPanels(submission)} />
        </DataLoader>
        <Matches matchKey="mmeMatch" submission={submission} loading={loading} />
      </DataLoader>
    </div>,
  ) : (
    <div>
      <Header
        size="small"
        content="No individuals from this family have been submitted"
        icon={<Icon name="warning sign" color="orange" />}
      />
      <a target="_blank" href={`/matchmaker/search/project/TODO/family/${family.familyId}`}>
        {/* TODO submit UI */}
        Submit to Match Maker Exchange
      </a>
    </div>
  )
)

Matchmaker.propTypes = {
  matchmakerSubmissions: PropTypes.array,
  family: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
  monarchLoading: PropTypes.bool,
  loadMonarch: PropTypes.func,
  searchMme: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  family: getFamiliesByGuid(state)[ownProps.match.params.familyGuid],
  matchmakerSubmissions: getFamilyMatchmakerSubmissions(state, ownProps),
  loading: getMatchmakerMatchesLoading(state),
  monarchLoading: getMonarchMatchesLoading(state),
})

const mapDispatchToProps = (dispatch) => {
  return {
    load: (individualId) => {
      return dispatch(loadMmeMatches(individualId))
    },
    searchMme: individualId => () => {
      return dispatch(loadMmeMatches(individualId, 'mme'))
    },
    loadMonarch: individualId => () => {
      return dispatch(loadMmeMatches(individualId, 'monarch'))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(Matchmaker)
