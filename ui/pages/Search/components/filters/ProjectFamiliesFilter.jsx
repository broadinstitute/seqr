import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Form, Button } from 'semantic-ui-react'

import {
  getProjectsByGuid,
  getFamiliesGroupedByProjectGuid,
  getAnalysisGroupsGroupedByProjectGuid,
  getFamiliesByGuid,
  getAnalysisGroupsByGuid,
  getProjectDatasetTypes,
} from 'redux/selectors'
import { Multiselect, ButtonRadioGroup } from 'shared/components/form/Inputs'
import { ProjectFilter } from 'shared/components/panel/search/ProjectsField'
import { SOLVED_FAMILY_STATUS_OPTIONS } from 'shared/utils/constants'
import { getSelectedAnalysisGroups } from '../../constants'
import { getProjectFamilies, getSearchContextIsLoading, getFamilyOptions, getAnalysisGroupOptions } from '../../selectors'
import { loadProjectFamiliesContext } from '../../reducers'

const ALL = 'ALL'
const UNSOLVED = 'UNSOLVED'
const MULTI_FAMILY_OPTIONS = [
  { text: 'All Families', value: ALL },
  { text: 'Unsolved', value: UNSOLVED },
  { text: 'Select', value: null },
]

const RadioGroupContainer = props => <Form.Field control={Button.Group} size="tiny" width={8} {...props} />

class ProjectFamiliesFilterInput extends React.PureComponent {

  static propTypes = {
    familyOptions: PropTypes.arrayOf(PropTypes.object),
    analysisGroupOptions: PropTypes.arrayOf(PropTypes.object),
    projectAnalysisGroupsByGuid: PropTypes.object,
    value: PropTypes.object,
    onChange: PropTypes.func,
  }

  multiFamiliesSelected = () => {
    const { familyOptions, value } = this.props
    if (!value.familyGuids || value.familyGuids.length === familyOptions.length) {
      return ALL
    }
    if (this.unsolvedFamilyGuids().sort().join(',') === value.familyGuids.sort().join(',')) {
      return UNSOLVED
    }
    return null
  }

  unsolvedFamilyGuids = () => {
    const { familyOptions } = this.props
    return familyOptions.filter(
      ({ analysisStatus }) => !SOLVED_FAMILY_STATUS_OPTIONS.has(analysisStatus),
    ).map((({ value }) => value))
  }

  selectedAnalysisGroups = () => {
    const { projectAnalysisGroupsByGuid, value } = this.props

    return this.multiFamiliesSelected() ? [] :
      getSelectedAnalysisGroups(projectAnalysisGroupsByGuid, value.familyGuids).map(group => group.analysisGroupGuid)
  }

  onFamiliesChange = (familyGuids) => {
    const { value, onChange } = this.props
    onChange({ ...value, familyGuids })
  }

  selectAnalysisGroup = (analysisGroups) => {
    const { projectAnalysisGroupsByGuid, value } = this.props

    const selectedAnalysisGroups = this.selectedAnalysisGroups()

    if (analysisGroups.length > selectedAnalysisGroups.length) {
      const newGroupGuid = analysisGroups.find(analysisGroupGuid => !selectedAnalysisGroups.includes(analysisGroupGuid))
      this.onFamiliesChange(
        [...new Set([...value.familyGuids, ...projectAnalysisGroupsByGuid[newGroupGuid].familyGuids])],
      )
    } else if (analysisGroups.length < selectedAnalysisGroups.length) {
      const removedGroupGuid = selectedAnalysisGroups.find(
        analysisGroupGuid => !analysisGroups.includes(analysisGroupGuid),
      )
      this.onFamiliesChange(value.familyGuids.filter(
        familyGuid => !projectAnalysisGroupsByGuid[removedGroupGuid].familyGuids.includes(familyGuid),
      ))
    }
  }

  selectAllFamilies = (value) => {
    const { familyOptions } = this.props
    if (value) {
      this.onFamiliesChange(value === UNSOLVED ?
        this.unsolvedFamilyGuids() : familyOptions.map((opt => opt.value)))
    } else {
      this.onFamiliesChange([])
    }
  }

  render() {
    const { familyOptions, analysisGroupOptions, projectAnalysisGroupsByGuid, value, onChange, ...props } = this.props
    const multiFamiliesSelected = this.multiFamiliesSelected()
    const selectedFamilies = multiFamiliesSelected ? [] : value.familyGuids

    return (
      <Form.Group inline widths="equal">
        <ButtonRadioGroup
          {...props}
          value={multiFamiliesSelected}
          onChange={this.selectAllFamilies}
          formGroupAs={RadioGroupContainer}
          options={MULTI_FAMILY_OPTIONS}
        />
        <Multiselect
          {...props}
          value={selectedFamilies}
          onChange={this.onFamiliesChange}
          options={familyOptions}
          disabled={!!multiFamiliesSelected}
          label="Families"
        />
        <Multiselect
          {...props}
          value={this.selectedAnalysisGroups()}
          onChange={this.selectAnalysisGroup}
          options={analysisGroupOptions}
          disabled={!!multiFamiliesSelected}
          label="Analysis Groups"
          color="pink"
        />
      </Form.Group>
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  familyOptions: getFamilyOptions(state, ownProps),
  analysisGroupOptions: getAnalysisGroupOptions(state, ownProps),
  projectAnalysisGroupsByGuid: getAnalysisGroupsGroupedByProjectGuid(state)[ownProps.value.projectGuid] || {},
  project: getProjectsByGuid(state)[ownProps.value.projectGuid],
  projectHasSamples: (getProjectDatasetTypes(state)[ownProps.value.projectGuid] || []).length > 0,
  loading: getSearchContextIsLoading(state),
  filterInputComponent: ProjectFamiliesFilterInput,
})

const mapDispatchToProps = (dispatch, ownProps) => {
  const onLoadSuccess = (state) => {
    const newVal = getProjectFamilies(
      ownProps.value, getFamiliesByGuid(state), getFamiliesGroupedByProjectGuid(state), getAnalysisGroupsByGuid(state),
    )
    if (newVal && newVal !== ownProps.value) {
      ownProps.onChange(newVal)
    }
  }

  return {
    load: (context) => {
      dispatch(loadProjectFamiliesContext(context, onLoadSuccess))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(ProjectFilter)
