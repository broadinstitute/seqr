import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'

import { updateProject } from 'redux/rootReducer'
import { PROJECT_FIELDS, GENOME_VERSION_37 } from 'shared/utils/constants'
import UpdateButton from 'shared/components/buttons/UpdateButton'

const DEFAULT_PROJECT = {
  genomeVersion: GENOME_VERSION_37,
}

const CreateProjectButton = props =>
  <UpdateButton
    buttonText="Create Project"
    buttonFloated="right"
    editIconName="plus"
    modalTitle="Create Project"
    modalId="createProject"
    onSubmit={props.updateProject}
    initialValues={DEFAULT_PROJECT}
    formFields={PROJECT_FIELDS}
  />

CreateProjectButton.propTypes = {
  updateProject: PropTypes.func.isRequired,
}

const mapDispatchToProps = {
  updateProject,
}

export default connect(null, mapDispatchToProps)(CreateProjectButton)

