import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'

import { updateProject } from 'redux/rootReducer'
import { getUser } from 'redux/selectors'
import { EDITABLE_PROJECT_FIELDS, GENOME_VERSION_FIELD, GENOME_VERSION_38 } from 'shared/utils/constants'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import { validators } from 'shared/components/form/FormHelpers'
import { BooleanCheckbox } from 'shared/components/form/Inputs'

const PROJECT_FIELDS = [
  ...EDITABLE_PROJECT_FIELDS,
  GENOME_VERSION_FIELD,
  { name: 'isDemo', label: 'Demo Project', component: BooleanCheckbox, inline: true },
  { name: 'disableMme', label: 'Disable Matchmaker', component: BooleanCheckbox, inline: true },
]

const ANVIL_PROJECT_FIELDS = [
  ...PROJECT_FIELDS,
  { name: 'workspaceNamespace', label: 'Workspace Namespace', validate: validators.required, width: 8, inline: true },
  { name: 'workspaceName', label: 'Workspace Name', validate: validators.required, width: 8, inline: true },
]

const DEFAULT_PROJECT = {
  genomeVersion: GENOME_VERSION_38,
}

const CreateProjectButton = React.memo(props => (
  <UpdateButton
    buttonText="Create Project"
    buttonFloated="right"
    editIconName="plus"
    modalTitle="Create Project"
    modalId="createProject"
    onSubmit={props.updateProject}
    initialValues={DEFAULT_PROJECT}
    formFields={props.user.isAnvil ? ANVIL_PROJECT_FIELDS : PROJECT_FIELDS}
    showErrorPanel
  />
))

CreateProjectButton.propTypes = {
  updateProject: PropTypes.func.isRequired,
  user: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

const mapDispatchToProps = {
  updateProject,
}

export default connect(mapStateToProps, mapDispatchToProps)(CreateProjectButton)
