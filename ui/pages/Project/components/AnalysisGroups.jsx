import React from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { Popup, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { getAnalysisGroupIsLoading } from 'redux/selectors'
import OptionFieldView from 'shared/components/panel/view-fields/OptionFieldView'
import DataLoader from 'shared/components/DataLoader'
import { HelpIcon } from 'shared/components/StyledComponents'
import { FAMILY_FIELD_NAME_LOOKUP, CATEGORY_FAMILY_FILTERS } from 'shared/utils/constants'
import { compareObjects } from 'shared/utils/sortUtils'
import { loadCurrentProjectAnalysisGroups } from '../reducers'
import { getProjectAnalysisGroupsByGuid, getProjectGuid } from '../selectors'
import { UpdateAnalysisGroupButton, DeleteAnalysisGroupButton } from './AnalysisGroupButtons'

const AnalysisGroups = React.memo(({ projectGuid, load, loading, analysisGroupsByGuid, analysisGroupGuid }) => (
  <DataLoader load={load} loading={loading} content={analysisGroupsByGuid}>
    {(analysisGroupsByGuid[analysisGroupGuid] ? [analysisGroupsByGuid[analysisGroupGuid]] : Object.values(analysisGroupsByGuid).sort(compareObjects('name'))).map(ag => (
      <div key={ag.name}>
        {ag.criteria && <Icon name="sync" size="small" />}
        <Link to={`/project/${projectGuid}/analysis_group/${ag.analysisGroupGuid}`}>{ag.name}</Link>
        <Popup
          position="right center"
          trigger={<HelpIcon />}
          content={ag.criteria ? Object.keys(ag.criteria).map(category => (
            <OptionFieldView
              key={category}
              field={category}
              initialValues={ag.criteria}
              fieldName={FAMILY_FIELD_NAME_LOOKUP[category]}
              tagOptions={CATEGORY_FAMILY_FILTERS[category]}
              multiple
            />
          )) : (
            <div>
              <b>{`${ag.familyGuids.length} Families`}</b>
              <br />
              <i>{ag.description}</i>
            </div>
          )}
          size="tiny"
        />
        <UpdateAnalysisGroupButton analysisGroup={ag} iconOnly />
        <DeleteAnalysisGroupButton analysisGroup={ag} iconOnly size="tiny" />
      </div>
    ))}
  </DataLoader>
))

AnalysisGroups.propTypes = {
  analysisGroupGuid: PropTypes.string,
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
