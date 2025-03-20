import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { FormSpy } from 'react-final-form'

import { configuredField } from 'shared/components/form/FormHelpers'
import { ButtonRadioGroup, BooleanCheckbox } from 'shared/components/form/Inputs'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { ButtonLink, InlineHeader } from 'shared/components/StyledComponents'
import { GENOME_VERSION_OPTIONS } from 'shared/utils/constants'
import { loadProjectGroupContext } from '../../reducers'
import ProjectFamiliesFilter from './ProjectFamiliesFilter'
import { AddProjectButton } from './ProjectsField'

const INCLUDE_ALL_PROJECTS = 'allGenomeProjectFamilies'

const INCLUDE_ALL_PROJECTS_FIELD = {
  name: INCLUDE_ALL_PROJECTS,
  component: ButtonRadioGroup,
  options: [
    ...GENOME_VERSION_OPTIONS.map(opt => ({ ...opt, color: 'black' })),
    { value: '', text: 'Custom', color: 'grey' },
  ],
}

const UNSOLVED_ONLY_FIELD = {
  name: 'unsolvedFamiliesOnly',
  component: BooleanCheckbox,
  label: 'Unsolved Families Only',
  inline: true,
}

const TRIO_ONLY_FIELD = {
  name: 'trioFamiliesOnly',
  component: BooleanCheckbox,
  label: 'Trio+ Families Only',
  inline: true,
}

const processAddedProject = result => ({ projectGuid: result.key })

const AddProjectFamiliesButton = props => <AddProjectButton processAddedElement={processAddedProject} {...props} />

const mapAddProjectDispatchToProps = {
  addProjectGroup: loadProjectGroupContext,
}

const validateFamilies = value => (value && value.familyGuids && value.familyGuids.length ? undefined : 'Families are required for all projects')

const PROJECT_FAMILIES_FIELD = {
  name: 'projectFamilies',
  component: ProjectFamiliesFilter,
  addArrayElement: connect(null, mapAddProjectDispatchToProps)(AddProjectFamiliesButton),
  validate: validateFamilies,
  isArrayField: true,
}

class AllProjectFamiliesField extends React.PureComponent {

  static propTypes = {
    numProjects: PropTypes.number,
  }

  state = { viewAllProjects: false }

  viewProjects = (e) => {
    e.preventDefault()
    this.setState({ viewAllProjects: true })
  }

  render() {
    const { numProjects } = this.props
    const { viewAllProjects } = this.state
    return numProjects < 20 || viewAllProjects ?
      configuredField(PROJECT_FAMILIES_FIELD) : <ButtonLink onClick={this.viewProjects} content={`Show all ${numProjects} searched projects`} />
  }

}

const SUBSCRIPTION = { values: true }

export default props => (
  <div>
    <InlineHeader content="Include All Projects: " />
    {configuredField(INCLUDE_ALL_PROJECTS_FIELD)}
    <HorizontalSpacer width={20} />
    {configuredField(UNSOLVED_ONLY_FIELD)}
    <HorizontalSpacer width={20} />
    {configuredField(TRIO_ONLY_FIELD)}
    <FormSpy subscription={SUBSCRIPTION}>
      {({ values }) => (
        !values[INCLUDE_ALL_PROJECTS] &&
          <AllProjectFamiliesField {...props} numProjects={(values.projectFamilies || []).length} />
      )}
    </FormSpy>
  </div>
)
