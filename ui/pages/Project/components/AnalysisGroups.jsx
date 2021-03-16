import React from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { HelpIcon } from 'shared/components/StyledComponents'
import { compareObjects } from 'shared/utils/sortUtils'
import { getProjectAnalysisGroupsByGuid, getCurrentProject } from '../selectors'
import { UpdateAnalysisGroupButton, DeleteAnalysisGroupButton } from './AnalysisGroupButtons'


const AnalysisGroups = React.memo(({ project, analysisGroupsByGuid }) =>
  Object.values(analysisGroupsByGuid).sort(compareObjects('name')).map(ag =>
    <div key={ag.name}>
      <Link to={`/project/${project.projectGuid}/analysis_group/${ag.analysisGroupGuid}`}>{ag.name}</Link>
      <Popup
        position="right center"
        trigger={<HelpIcon />}
        content={<div><b>{ag.familyGuids.length} Families</b><br /><i>{ag.description}</i></div>}
        size="tiny"
      />
      <UpdateAnalysisGroupButton analysisGroup={ag} iconOnly />
      <DeleteAnalysisGroupButton analysisGroup={ag} iconOnly size="tiny" />
    </div>))


AnalysisGroups.propTypes = {
  project: PropTypes.object,
  analysisGroupsByGuid: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getCurrentProject(state),
  analysisGroupsByGuid: getProjectAnalysisGroupsByGuid(state),
})

export default connect(mapStateToProps)(AnalysisGroups)
