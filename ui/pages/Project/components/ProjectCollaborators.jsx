import React from 'react'
import PropTypes from 'prop-types'
import orderBy from 'lodash/orderBy'
import { Icon, Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { HorizontalSpacer } from 'shared/components/Spacers'
import DeleteButton from 'shared/components/buttons/DeleteButton'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import { RadioGroup } from 'shared/components/form/Inputs'
import { validators } from 'shared/components/form/ReduxFormWrapper'

import { updateCollaborator } from '../reducers'
import { getProject } from '../selectors'

const NAME_FIELDS = [
  {
    name: 'firstName',
    label: 'First Name',
    width: 8,
    inline: true,
  },
  {
    name: 'lastName',
    label: 'Last Name',
    width: 8,
    inline: true,
  },
]

const CREATE_FIELDS = [
  {
    name: 'email',
    label: 'Email',
    validate: validators.required,
  },
  ...NAME_FIELDS,
]

const EDIT_FIELDS = [
  {
    name: 'hasEditPermissions',
    label: 'Access Level',
    component: RadioGroup,
    options: [{ value: false, text: 'Collaborator' }, { value: true, text: 'Manager' }],
  },
  ...NAME_FIELDS,
]


const mapStateToProps = state => ({
  project: getProject(state),
})

const mapDispatchToProps = {
  onSubmit: updateCollaborator,
}

const AddCollaboratorButton = ({ project, onSubmit }) => (
  project.canEdit ?
    <UpdateButton
      modalId="addCollaborator"
      modalTitle="Add Collaborator"
      onSubmit={onSubmit}
      formFields={CREATE_FIELDS}
      editIconName="plus"
      buttonText="Add Collaborator"
      showErrorPanel
    /> : null
)

AddCollaboratorButton.propTypes = {
  project: PropTypes.object,
  onSubmit: PropTypes.func,
}

export const AddProjectCollaboratorButton = connect(mapStateToProps, mapDispatchToProps)(AddCollaboratorButton)

const ProjectCollaborators = ({ project, onSubmit }) => (
  orderBy(project.collaborators, [c => c.hasEditPermissions, c => c.email], ['desc', 'asc']).map((c, i) =>
    <div key={c.email}>
      <Popup
        position="top center"
        trigger={<Icon link name={c.hasEditPermissions ? 'star' : ''} />}
        content={c.hasEditPermissions ? 'Has "Manager" permissions' : ''}
        size="small"
      />
      {c.displayName ? `${c.displayName} ▪ ` : null}
      {
         c.email ?
           <i><a href={`mailto:${c.email}`}>{c.email}</a></i> : null
      }
      {project.canEdit &&
        <span>
          <HorizontalSpacer width={10} />
          <UpdateButton
            modalId={`editCollaborator-${c.email}`}
            modalTitle={`Edit Collaborator: ${c.displayName || c.email}`}
            onSubmit={onSubmit}
            formFields={EDIT_FIELDS}
            initialValues={c}
            showErrorPanel
          />
          <DeleteButton
            initialValues={c}
            onSubmit={onSubmit}
            confirmDialog={
              <div className="content">
                Are you sure you want to delete <b>{c.displayName || c.email}</b>. They will still have their user account
                 and be able to log in, but will not be able to access this project anymore.
              </div>
            }
          />
        </span>

      }
    </div>,
  )
)


ProjectCollaborators.propTypes = {
  project: PropTypes.object.isRequired,
}

export default connect(mapStateToProps, mapDispatchToProps)(ProjectCollaborators)
