import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { loadFamilyProject } from 'redux/rootReducer'
import { getProjectsByGuid, getFamiliesByGuid, getProjectDetailsIsLoading } from 'redux/selectors'
import { BaseSemanticInput } from 'shared/components/form/Inputs'
import DataLoader from 'shared/components/DataLoader'


const FamiliesFilter = ({ value, familiesByGuid, project, loading, load, ...props }) =>
  <DataLoader contentId={value} loading={loading} load={load} content={project}>
    {/* TODO handle multiple families */}
    <BaseSemanticInput {...props} label={project && project.name} value={(familiesByGuid[value.familyGuids[0]] || {}).displayName} inputType="Input" />
  </DataLoader>

const mapStateToProps = (state, ownProps) => ({
  familiesByGuid: getFamiliesByGuid(state),
  project: getProjectsByGuid(state)[ownProps.value.projectGuid || (getFamiliesByGuid(state)[ownProps.value.familyGuids[0]] || {}).projectGuid],
  loading: getProjectDetailsIsLoading(state),
})

const mapDispatchToProps = {
  load: loadFamilyProject,
}

FamiliesFilter.propTypes = {
  loading: PropTypes.bool,
  value: PropTypes.arrayOf(PropTypes.string),
  load: PropTypes.func,
  project: PropTypes.object,
  familiesByGuid: PropTypes.object,
}


export default connect(mapStateToProps, mapDispatchToProps)(FamiliesFilter)
