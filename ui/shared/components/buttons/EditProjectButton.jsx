import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'

import { updateProject } from 'redux/rootReducer'
import UpdateButton from './UpdateButton'
import { EDITABLE_PROJECT_FIELDS, MATCHMAKER_CONTACT_NAME_FIELD, MATCHMAKER_CONTACT_URL_FIELD } from '../../utils/constants'

const MATCHMAKER_PROJECT_FIELDS = [
  ...EDITABLE_PROJECT_FIELDS,
  ...[
    { ...MATCHMAKER_CONTACT_NAME_FIELD, name: 'mmePrimaryDataOwner' },
    { ...MATCHMAKER_CONTACT_URL_FIELD, name: 'mmeContactUrl' },
  ].map(({ label, ...field }) => ({ ...field, label: `Matchmaker ${label}` })),
]

const EDITABLE_FIELD_KEYS = ['projectGuid', ...MATCHMAKER_PROJECT_FIELDS.map(({ name }) => name)]

const EditProjectButton = React.memo(props => (
  props.project && props.project.canEdit ? (
    <UpdateButton
      buttonText="Edit Project"
      modalTitle="Edit Project"
      modalId={`editProject-${props.project.projectGuid}`}
      onSubmit={props.updateProject}
      formFields={props.project.isMmeEnabled ? MATCHMAKER_PROJECT_FIELDS : EDITABLE_PROJECT_FIELDS}
      initialValues={props.project}
      trigger={props.trigger}
      submitButtonText="Save"
    />
  ) : null
))

EditProjectButton.propTypes = {
  project: PropTypes.object,
  updateProject: PropTypes.func,
  trigger: PropTypes.node,
}

const mapDispatchToProps = {
  updateProject: updates => updateProject(Object.entries(updates).reduce((acc, [k, v]) => (
    EDITABLE_FIELD_KEYS.includes(k) ? { ...acc, [k]: v } : acc
  ), {})),
}

export default connect(null, mapDispatchToProps)(EditProjectButton)
