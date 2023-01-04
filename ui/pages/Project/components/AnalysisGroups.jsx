import React from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { getAnalysisGroupIsLoading } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { HelpIcon } from 'shared/components/StyledComponents'
import { compareObjects } from 'shared/utils/sortUtils'
import { loadCurrentProjectAnalysisGroups } from '../reducers'
import { getProjectAnalysisGroupsByGuid, getProjectGuid } from '../selectors'
import { UpdateAnalysisGroupButton, DeleteAnalysisGroupButton } from './AnalysisGroupButtons'

const AnalysisGroups = React.memo(({ projectGuid, load, loading, analysisGroupsByGuid }) => (
  <DataLoader load={load} loading={loading} content={analysisGroupsByGuid}>
    {Object.values(analysisGroupsByGuid).sort(compareObjects('name')).map(ag => (
      <div key={ag.name}>
        <Link to={`/project/${projectGuid}/analysis_group/${ag.analysisGroupGuid}`}>{ag.name}</Link>
        <Popup
          position="right center"
          trigger={<HelpIcon />}
          content={
            <div>
              <b>{`${ag.familyGuids.length} Families`}</b>
              <br />
              <i>{ag.description}</i>
            </div>
          }
          size="tiny"
        />
        <UpdateAnalysisGroupButton analysisGroup={ag} iconOnly />
        <DeleteAnalysisGroupButton analysisGroup={ag} iconOnly size="tiny" />
      </div>
    ))}
  </DataLoader>
))

AnalysisGroups.propTypes = {
  projectGuid: PropTypes.string,
  analysisGroupsByGuid: PropTypes.object.isRequired,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = state => ({
  projectGuid: getProjectGuid(state),
  analysisGroupsByGuid: getProjectAnalysisGroupsByGuid(state),
  loading: getAnalysisGroupIsLoading(state),
})

const mapDispatchToProps = {
  load: loadCurrentProjectAnalysisGroups,
}

export default connect(mapStateToProps, mapDispatchToProps)(AnalysisGroups)
