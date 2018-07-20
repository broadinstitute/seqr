import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Header, Icon } from 'semantic-ui-react'

import { loadMmeMatches } from 'redux/rootReducer'
import { getProjectsByGuid, getMatchmakerSubmissions, getMatchmakerMatches, getMatchmakerMatchesLoading } from 'redux/selectors'
import Modal from './Modal'
import ButtonLink from '../buttons/ButtonLink'
import DataLoader from '../DataLoader'


const MatchmakerModal = ({ project, family, loading, load, matchmakerSubmissions, matchmakerMatches }) =>
  <Modal
    trigger={<ButtonLink>Match Maker Exchange</ButtonLink>}
    title={`${family.displayName}: Match Maker Exchange`}
    modalName={`mme-${family.familyGuid}`}
    size="large"
  >
    {matchmakerSubmissions ? Object.keys(matchmakerSubmissions).map(individualId =>
      <div key={individualId}>
        <Header size="medium" disabled content={individualId} dividing />
        <DataLoader contentId={individualId} content={matchmakerMatches[individualId]} loading={loading} load={load}>
          {JSON.stringify(matchmakerMatches[individualId])}
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

MatchmakerModal.propTypes = {
  matchmakerSubmissions: PropTypes.object,
  matchmakerMatches: PropTypes.object,
  project: PropTypes.object,
  family: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[ownProps.family.projectGuid],
  matchmakerSubmissions: getMatchmakerSubmissions(state)[ownProps.family.projectGuid][ownProps.family.familyId],
  matchmakerMatches: getMatchmakerMatches(state)[ownProps.family.projectGuid] || {},
  loading: getMatchmakerMatchesLoading(state),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    load: (individualId) => {
      return dispatch(loadMmeMatches(individualId, ownProps.family))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(MatchmakerModal)
