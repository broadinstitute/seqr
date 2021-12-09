import React from 'react'
import PropTypes from 'prop-types'
import orderBy from 'lodash/orderBy'
import { Icon, Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'
import styled from 'styled-components'

import { loadUserOptions } from 'redux/rootReducer'
import { getUserOptionsIsLoading } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { HorizontalSpacer } from 'shared/components/Spacers'
import DeleteButton from 'shared/components/buttons/DeleteButton'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import { RadioGroup, AddableSelect } from 'shared/components/form/Inputs'
import { USER_NAME_FIELDS } from 'shared/utils/constants'

import { updateCollaborator } from '../reducers'
import { getUserOptions, getCurrentProject } from '../selectors'

const CollaboratorEmailDropdown = React.memo(({ load, ...props }) => (
  <DataLoader load={load} loading={false} content>
    <AddableSelect additionLabel="New Collaborator: " {...props} />
  </DataLoader>
))

CollaboratorEmailDropdown.propTypes = {
  load: PropTypes.func,
  loading: PropTypes.bool,
  onChange: PropTypes.func,
  value: PropTypes.object,
}

const mapDropdownStateToProps = state => ({
  loading: getUserOptionsIsLoading(state),
  options: getUserOptions(state),
})

const mapDropdownDispatchToProps = {
  load: loadUserOptions,
}

const CREATE_FIELDS = [
  {
    name: 'user',
    label: 'Email',
    component: connect(mapDropdownStateToProps, mapDropdownDispatchToProps)(CollaboratorEmailDropdown),
    format: value => value && (value.username ? value : value.email),
    normalize: value => (typeof value === 'object' ? value : { email: value }),
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
]

const AddCollaboratorButton = React.memo(({ onSubmit }) => (
  <UpdateButton
    modalId="addCollaborator"
    modalTitle="Add Collaborator"
    onSubmit={onSubmit}
    formFields={CREATE_FIELDS}
    editIconName="plus"
    buttonText="Add Collaborator"
    showErrorPanel
  />
))

AddCollaboratorButton.propTypes = {
  onSubmit: PropTypes.func,
}

const CollaboratorContainer = styled.div`
  white-space: nowrap;
`

const CollaboratorRow = React.memo(({ collaborator, update }) => (
  <CollaboratorContainer>
    {update && (
      <span>
        <HorizontalSpacer width={10} />
        <UpdateButton
          modalId={`editCollaborator-${collaborator.email}`}
          modalTitle={`Edit Collaborator: ${collaborator.displayName || collaborator.email}`}
          onSubmit={update}
          formFields={EDIT_FIELDS}
          initialValues={collaborator}
          showErrorPanel
          size="tiny"
        />
        <DeleteButton
          initialValues={collaborator}
          onSubmit={update}
          size="tiny"
          hideNoRequestStatus
          confirmDialog={
            <div className="content">
              Are you sure you want to delete &nbsp;
              <b>{collaborator.displayName || collaborator.email}</b>
              . They will still
              have their user account and be able to log in, but will not be able to access this project anymore.
            </div>
          }
        />
      </span>
    )}
    <Popup
      position="top center"
      trigger={<Icon link size="small" name={collaborator.hasEditPermissions ? 'star' : ''} />}
      content={`Has "${collaborator.hasEditPermissions ? 'Manager' : 'Collaborator'}" permissions`}
      size="small"
    />
    {collaborator.displayName && `${collaborator.displayName} - `}
    <a href={`mailto:${collaborator.email}`}>{collaborator.email}</a>
  </CollaboratorContainer>
))

CollaboratorRow.propTypes = {
  collaborator: PropTypes.object.isRequired,
  update: PropTypes.func,
}

const getSortedCollabs = (project, isAnvil) => orderBy(
  project.collaborators.filter(col => col.isAnvil === isAnvil), [c => c.hasEditPermissions, c => c.email],
  ['desc', 'asc'],
)

const ProjectCollaborators = React.memo(({ project, onSubmit, addCollaborator }) => {
  const localCollabs = getSortedCollabs(project, false)
  const anvilCollabs = getSortedCollabs(project, true)
  return [
    localCollabs.map(
      c => <CollaboratorRow key={c.username} collaborator={c} update={project.canEdit ? onSubmit : null} />,
    ),
    ((project.canEdit && !project.workspaceName) ? (
      <div key="addButton">
        <br />
        <AddCollaboratorButton onSubmit={addCollaborator} />
      </div>
    ) : null),
    (localCollabs.length && anvilCollabs.length) ? (
      <p key="subheader">
        <br />
        AnVIL Workspace Users
      </p>
    ) : null,
    anvilCollabs.map(c => <CollaboratorRow key={c.username} collaborator={c} />),
  ]
})

ProjectCollaborators.propTypes = {
  project: PropTypes.object.isRequired,
  onSubmit: PropTypes.func,
  addCollaborator: PropTypes.func,
}

const mapStateToProps = state => ({
  project: getCurrentProject(state),
})

const mapDispatchToProps = {
  onSubmit: updateCollaborator,
  addCollaborator: updates => updateCollaborator(updates.user),
}

export default connect(mapStateToProps, mapDispatchToProps)(ProjectCollaborators)
