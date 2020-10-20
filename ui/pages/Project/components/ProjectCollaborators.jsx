import React from 'react'
import PropTypes from 'prop-types'
import orderBy from 'lodash/orderBy'
import { Icon, Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'
import styled from 'styled-components'

import { loadUserOptions } from 'redux/rootReducer'
import { getUsersByUsername, getCurrentProject, getUserOptionsIsLoading } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { HorizontalSpacer } from 'shared/components/Spacers'
import DeleteButton from 'shared/components/buttons/DeleteButton'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import { RadioGroup, AddableSelect } from 'shared/components/form/Inputs'
import { USER_NAME_FIELDS } from 'shared/utils/constants'

import { updateCollaborator } from '../reducers'
import { getUserOptions } from '../selectors'


const CollaboratorEmailDropdown = React.memo(({ load, loading, usersByUsername, onChange, value, ...props }) =>
  <DataLoader load={load} loading={false} content>
    <AddableSelect
      loading={loading}
      additionLabel="New Collaborator: "
      onChange={val => onChange(usersByUsername[val] || { email: val })}
      value={value.username || value.email}
      {...props}
    />
  </DataLoader>,
)

CollaboratorEmailDropdown.propTypes = {
  load: PropTypes.func,
  loading: PropTypes.bool,
  usersByUsername: PropTypes.object,
  onChange: PropTypes.func,
  value: PropTypes.any,
}

const mapDropdownStateToProps = state => ({
  loading: getUserOptionsIsLoading(state),
  options: getUserOptions(state),
  usersByUsername: getUsersByUsername(state),
})

const mapDropdownDispatchToProps = {
  load: loadUserOptions,
}

const CREATE_FIELDS = [
  {
    name: 'user',
    label: 'Email',
    component: connect(mapDropdownStateToProps, mapDropdownDispatchToProps)(CollaboratorEmailDropdown),
    validate: value => (
      /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$/i.test((value || {}).email) ? undefined : 'Invalid email address'
    ),
    width: 16,
    inline: true,
  },
  ...USER_NAME_FIELDS.map(({ name, ...field }) => ({ ...field, name: `user.${name}` })),
]

const EDIT_FIELDS = [
  {
    name: 'hasEditPermissions',
    label: 'Access Level',
    component: RadioGroup,
    options: [{ value: false, text: 'Collaborator' }, { value: true, text: 'Manager' }],
  },
  ...USER_NAME_FIELDS,
]


const AddCollaboratorButton = React.memo(({ project, onSubmit }) => (
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
))

AddCollaboratorButton.propTypes = {
  project: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapStateToProps = state => ({
  project: getCurrentProject(state),
})

const mapCreateDispatchToProps = {
  onSubmit: updates => updateCollaborator(updates.user),
}

export const AddProjectCollaboratorButton = connect(mapStateToProps, mapCreateDispatchToProps)(AddCollaboratorButton)

const CollaboratorContainer = styled.div`
  white-space: nowrap;
`

const ProjectCollaborators = React.memo(({ project, anvilCollaborator, onSubmit }) => (
  <div>{anvilCollaborator && project.collaborators.filter(col => col.isAnvil === anvilCollaborator).length > 0 && <p>AnVIL Workspace Users</p>}{
  orderBy(project.collaborators.filter(col => col.isAnvil === anvilCollaborator), [c => c.hasEditPermissions, c => c.email], ['desc', 'asc']).map(c =>
    <CollaboratorContainer key={c.username}>
      {project.canEdit && !c.isAnvil &&
        <span>
          <HorizontalSpacer width={10} />
          <UpdateButton
            modalId={`editCollaborator-${c.email}`}
            modalTitle={`Edit Collaborator: ${c.displayName || c.email}`}
            onSubmit={onSubmit}
            formFields={EDIT_FIELDS}
            initialValues={c}
            showErrorPanel
            size="tiny"
          />
          <DeleteButton
            initialValues={c}
            onSubmit={onSubmit}
            size="tiny"
            hideNoRequestStatus
            confirmDialog={
              <div className="content">
                Are you sure you want to delete <b>{c.displayName || c.email}</b>. They will still have their user account
                and be able to log in, but will not be able to access this project anymore.
              </div>
            }
          />
        </span>
      }
      <Popup
        position="top center"
        trigger={<Icon link size="small" name={c.hasEditPermissions ? 'star' : ''} />}
        content={`Has "${c.hasEditPermissions ? 'Manager' : 'Collaborator'}" permissions`}
        size="small"
      />
      {c.displayName && `${c.displayName} - `}
      <a href={`mailto:${c.email}`}>{c.email}</a>
    </CollaboratorContainer>,
  )}
  </div>
))


ProjectCollaborators.propTypes = {
  project: PropTypes.object.isRequired,
  anvilCollaborator: PropTypes.bool.isRequired,
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = {
  onSubmit: updateCollaborator,
}

export default connect(mapStateToProps, mapDispatchToProps)(ProjectCollaborators)
