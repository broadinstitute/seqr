import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'

import { updateProject } from 'redux/rootReducer'
import UpdateButton from './UpdateButton'
import {
  EDITABLE_PROJECT_FIELDS,
  PM_EDITABLE_PROJECT_FIELDS,
  MATCHMAKER_CONTACT_NAME_FIELD,
  MATCHMAKER_CONTACT_URL_FIELD,
} from '../../utils/constants'

const MATCHMAKER_PROJECT_FIELDS = [
  { ...MATCHMAKER_CONTACT_NAME_FIELD, name: 'mmePrimaryDataOwner' },
  { ...MATCHMAKER_CONTACT_URL_FIELD, name: 'mmeContactUrl' },
].map(({ label, ...field }) => ({ ...field, label: `Matchmaker ${label}` }))

// Field mapping based on whether project has matchmaker and user is a PM. Usage: FIELD_LOOKUP[isMmeEnabled][isPm]
const FIELD_LOOKUP = {
  true: {
    true: [...PM_EDITABLE_PROJECT_FIELDS, ...MATCHMAKER_PROJECT_FIELDS],
    false: [...EDITABLE_PROJECT_FIELDS, ...MATCHMAKER_PROJECT_FIELDS],
  },
  false: { true: PM_EDITABLE_PROJECT_FIELDS, false: EDITABLE_PROJECT_FIELDS },
}

const EDITABLE_FIELD_KEYS = ['projectGuid', ...FIELD_LOOKUP.true.true.map(({ name }) => name)]

const EditProjectButton = React.memo(props => (
  props.project && props.project.canEdit ? (
    <UpdateButton
      buttonText="Edit Project"
      modalTitle="Edit Project"
      modalId={`editProject-${props.project.projectGuid}`}
      onSubmit={props.updateProject}
      formFields={FIELD_LOOKUP[props.project.isMmeEnabled][props.user.isPm]}
      initialValues={props.project}
      trigger={props.trigger}
      submitButtonText="Save"
    />
  ) : null
))

EditProjectButton.propTypes = {
  project: PropTypes.object,
  user: PropTypes.object,
  updateProject: PropTypes.func,
  trigger: PropTypes.node,
}

const mapDispatchToProps = {
  updateProject: updates => updateProject(Object.entries(updates).reduce((acc, [k, v]) => (
    EDITABLE_FIELD_KEYS.includes(k) ? { ...acc, [k]: v } : acc
  ), {})),
}

export default connect(null, mapDispatchToProps)(EditProjectButton)
