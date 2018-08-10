import React from 'react'
import PropTypes from 'prop-types'
import { withRouter } from 'react-router-dom'
import { connect } from 'react-redux'

import UpdateButton from 'shared/components/buttons/UpdateButton'
import DeleteButton from 'shared/components/buttons/DeleteButton'
import PedigreeImagePanel from 'shared/components/panel/view-pedigree-image/PedigreeImagePanel'
import { SelectableTableFormInput } from 'shared/components/table/SortableTable'
import {
  FAMILY_DISPLAY_NAME,
  FAMILY_FIELD_PEDIGREE,
  FAMILY_FIELD_DESCRIPTION,
} from 'shared/utils/constants'

import { updateAnalysisGroup } from '../reducers'
import { getProject, getProjectFamiliesByGuid } from '../selectors'


const FAMILY_FIELDS = [
  { name: FAMILY_DISPLAY_NAME, width: 3, content: 'Family' },
  {
    name: FAMILY_FIELD_PEDIGREE,
    width: 3,
    content: 'Pedigree',
    format: family => <PedigreeImagePanel family={family} disablePedigreeZoom compact />,
  },
  { name: FAMILY_FIELD_DESCRIPTION, width: 9, content: 'Description' },
]

const FORM_FIELDS = [
  { name: 'name', label: 'Name', validate: value => (value ? undefined : 'Name is required') },
  { name: 'description', label: 'Description' },
  {
    name: 'familyGuids',
    component: SelectableTableFormInput,
    idField: 'familyGuid',
    defaultSortColumn: FAMILY_DISPLAY_NAME,
    columns: FAMILY_FIELDS,
    validate: value => ((value && value.length) ? undefined : 'Families are required'),
    normalize: (value, previousValue) => (value instanceof Object ? Object.keys(value).filter(key => value[key]) : previousValue),
    format: value => (value || []).reduce((acc, key) => ({ ...acc, [key]: true }), {}),
  },
]

const UpdateAnalysisGroup = ({ project, analysisGroup, onSubmit, projectFamiliesByGuid }) => {
  if (!project.canEdit) {
    return null
  }
  const title = `${analysisGroup ? 'Edit' : 'Create New'} Analysis Group`
  const buttonProps = analysisGroup ?
    { modalId: `editAnalysisGroup-${analysisGroup.analysisGroupGuid}`, initialValues: analysisGroup } :
    { modalId: `createAnalysisGroup-${project.projectGuid}`, initialValues: { projectGuid: project.projectGuid }, editIconName: 'plus' }

  const fields = [...FORM_FIELDS]
  fields[2].data = Object.values(projectFamiliesByGuid)

  return <UpdateButton
    modalTitle={title}
    buttonText={title}
    onSubmit={onSubmit}
    formFields={fields}
    showErrorPanel
    {...buttonProps}
  />
}

UpdateAnalysisGroup.propTypes = {
  project: PropTypes.object,
  analysisGroup: PropTypes.object,
  projectFamiliesByGuid: PropTypes.object,
  onSubmit: PropTypes.func,
}


const DeleteAnalysisGroup = ({ project, analysisGroup, onSubmit, size, iconOnly, history }) => (
  project.canEdit ? <DeleteButton
    initialValues={analysisGroup}
    onSubmit={onSubmit}
    confirmDialog={<div className="content">Are you sure you want to delete <b>{analysisGroup.name}</b></div>}
    buttonText={iconOnly ? null : 'Delete AnalysisGroup'}
    size={size}
    onSuccess={() => history.push(`/project/${analysisGroup.projectGuid}/project_page`)}
  /> : null
)

DeleteAnalysisGroup.propTypes = {
  onSubmit: PropTypes.func,
  project: PropTypes.object,
  analysisGroup: PropTypes.object,
  iconOnly: PropTypes.bool,
  size: PropTypes.string,
  history: PropTypes.object,
}

const mapStateToProps = state => ({
  project: getProject(state),
  projectFamiliesByGuid: getProjectFamiliesByGuid(state),
})

const mapDispatchToProps = {
  onSubmit: updateAnalysisGroup,
}

export const UpdateAnalysisGroupButton = connect(mapStateToProps, mapDispatchToProps)(UpdateAnalysisGroup)
export const DeleteAnalysisGroupButton = withRouter(connect(mapStateToProps, mapDispatchToProps)(DeleteAnalysisGroup))

