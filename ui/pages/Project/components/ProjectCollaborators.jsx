import React from 'react'
import PropTypes from 'prop-types'
import { Icon, Popup, Segment, Header } from 'semantic-ui-react'
import { connect } from 'react-redux'
import styled from 'styled-components'

import { loadUserOptions } from 'redux/rootReducer'
import { getUserOptionsIsLoading, getUser } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { HorizontalSpacer } from 'shared/components/Spacers'
import DeleteButton from 'shared/components/buttons/DeleteButton'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import { RadioGroup, AddableSelect } from 'shared/components/form/Inputs'
import { validators } from 'shared/components/form/FormHelpers'
import LoadOptionsSelect from 'shared/components/form/LoadOptionsSelect'
import { HelpIcon } from 'shared/components/StyledComponents'
import { USER_NAME_FIELDS } from 'shared/utils/constants'

import { updateCollaborator, updateCollaboratorGroup, loadProjectCollaborators } from '../reducers'
import { getUserOptions, getCurrentProject, getProjectCollaboratorsIsLoading } from '../selectors'

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
    parse: value => (typeof value === 'object' ? value : { email: value }),
    validate: value => validators.requiredEmail((value || {}).email),
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

const CREATE_GROUP_FIELDS = [
  {
    name: 'name',
    label: 'Group',
    component: LoadOptionsSelect,
    url: '/api/users/get_group_options',
    optionsResponseKey: 'groups',
    validationErrorHeader: 'No User Groups Available',
    validationErrorMessage: 'Contact your system administrator to have them configure user groups',
    validate: validators.required,
  },
  ...EDIT_FIELDS,
]

const CollaboratorContainer = styled.div`
  white-space: nowrap;
`

const ProjectAccessSection = (
  { entities, idField, title, displayField, deleteMessage, rowDisplay, canEdit, onSubmit, onAdd, addEntityFields },
) => ([
  ...(entities || []).map(entity => (
    <CollaboratorContainer key={entity[idField]}>
      {canEdit && (
        <span>
          <HorizontalSpacer width={10} />
          <UpdateButton
            modalId={`edit${title}-${entity[idField]}`}
            modalTitle={`Edit ${title}: ${entity[displayField] || entity[idField]}`}
            onSubmit={onSubmit}
            formFields={EDIT_FIELDS}
            initialValues={entity}
            showErrorPanel
            size="tiny"
          />
          <DeleteButton
            initialValues={entity}
            onSubmit={onSubmit}
            size="tiny"
            hideNoRequestStatus
            confirmDialog={
              <div className="content">
                Are you sure you want to remove &nbsp;
                <b>{entity[displayField] || entity[idField]}</b>
                ?
                {deleteMessage}
              </div>
            }
          />
        </span>
      )}
      <Popup
        position="top center"
        trigger={<Icon link size="small" name={entity.hasEditPermissions ? 'star' : ''} />}
        content={`Has "${entity.hasEditPermissions ? 'Manager' : 'Collaborator'}" permissions`}
        size="small"
      />
      {rowDisplay(entity)}
    </CollaboratorContainer>
  )),
  (canEdit ? (
    <div key={`add${title}Button`}>
      <br />
      <UpdateButton
        modalId={`add${title}`}
        modalTitle={`Add ${title}`}
        onSubmit={onAdd}
        formFields={addEntityFields}
        editIconName="plus"
        buttonText={`Add ${title}`}
        showErrorPanel
      />
    </div>
  ) : null),
])

ProjectAccessSection.propTypes = {
  entities: PropTypes.arrayOf(PropTypes.object),
  onSubmit: PropTypes.func,
  onAdd: PropTypes.func,
  canEdit: PropTypes.bool,
  title: PropTypes.string,
  idField: PropTypes.string,
  displayField: PropTypes.string,
  deleteMessage: PropTypes.string,
  rowDisplay: PropTypes.func,
  addEntityFields: PropTypes.arrayOf(PropTypes.object),
}

const collaboratorDisplay = ({ displayName, email }) => (
  <span>
    {displayName && `${displayName} - `}
    <a href={`mailto:${email}`}>{email}</a>
  </span>
)

const groupNameDisplay = ({ name }) => name

const ProjectCollaborators = React.memo(({
  canEdit, workspaceName, collaborators, collaboratorGroups, user, loading, load, onSubmit, onGroupSubmit,
  addCollaborator,
}) => {
  const canEditCollaboratots = canEdit && !user.isAnvil
  return (
    <DataLoader load={load} loading={loading} content={collaborators}>
      <ProjectAccessSection
        title="Collaborator"
        idField="email"
        displayField="displayName"
        deleteMessage=" They will still have their user account and be able to log in, but will not be able to access this project anymore."
        entities={collaborators}
        canEdit={canEditCollaboratots}
        onSubmit={onSubmit}
        onAdd={addCollaborator}
        addEntityFields={CREATE_FIELDS}
        rowDisplay={collaboratorDisplay}
      />
      {collaboratorGroups?.length > 0 && <Header subheader="Groups" size="small" />}
      <ProjectAccessSection
        title="Collaborator Group"
        idField="name"
        entities={collaboratorGroups}
        canEdit={canEditCollaboratots}
        onSubmit={onGroupSubmit}
        onAdd={onGroupSubmit}
        addEntityFields={CREATE_GROUP_FIELDS}
        rowDisplay={groupNameDisplay}
      />
      {user.isAnvil && workspaceName && (
        <Segment basic size="small" textAlign="right">
          <i>Collaborators fetched from AnVIL</i>
          {canEdit && (
            <Popup
              trigger={<HelpIcon color="black" />}
              content={`Project collaborators are managed in AnVIL. Users with access to the associated workspace have
              access to this project. Users with "Writer" or "Owner" access to the workspace have Manager level access. 
              To add or remove users, or to change a user's access level, edit the collaborators directly in AnVIL`}
            />
          )}
        </Segment>
      )}
    </DataLoader>
  )
})

ProjectCollaborators.propTypes = {
  user: PropTypes.object.isRequired,
  canEdit: PropTypes.bool,
  workspaceName: PropTypes.string,
  collaborators: PropTypes.arrayOf(PropTypes.object),
  collaboratorGroups: PropTypes.arrayOf(PropTypes.object),
  loading: PropTypes.bool,
  load: PropTypes.func,
  onSubmit: PropTypes.func,
  onGroupSubmit: PropTypes.func,
  addCollaborator: PropTypes.func,
}

const mapStateToProps = (state) => {
  const { canEdit, workspaceName, collaborators, collaboratorGroups } = getCurrentProject(state)
  return {
    canEdit,
    workspaceName,
    collaborators,
    collaboratorGroups,
    user: getUser(state),
    loading: getProjectCollaboratorsIsLoading(state),
  }
}

const mapDispatchToProps = {
  load: loadProjectCollaborators,
  onSubmit: updateCollaborator,
  onGroupSubmit: updateCollaboratorGroup,
  addCollaborator: updates => updateCollaborator(updates.user),
}

export default connect(mapStateToProps, mapDispatchToProps)(ProjectCollaborators)
