import React from 'react'
import PropTypes from 'prop-types'
import { withRouter } from 'react-router-dom'
import { connect } from 'react-redux'

import { getCurrentProject } from 'redux/selectors'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import DeleteButton from 'shared/components/buttons/DeleteButton'
import FileUploadField from 'shared/components/form/XHRUploaderField'
import PedigreeImagePanel from 'shared/components/panel/view-pedigree-image/PedigreeImagePanel'
import { SelectableTableFormInput } from 'shared/components/table/SortableTable'
import {
  FAMILY_DISPLAY_NAME,
  FAMILY_FIELD_PEDIGREE,
  FAMILY_FIELD_DESCRIPTION,
} from 'shared/utils/constants'

import { updateAnalysisGroup } from '../reducers'
import { getProjectFamiliesByGuid } from '../selectors'


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


const FamilySelectorField = ({ value, onChange, families }) =>
  <div>
    <FileUploadField
      name="uploadedFamilyIds"
      normalize={(newValue, previousValue) => {
       if (newValue.errors) {
          return { ...newValue, info: newValue.errors, errors: [] }
        }
        if (newValue.parsedData && newValue.uploadedFileId !== (previousValue || {}).uploadedFileId) {
          const familyIdMap = families.reduce((acc, family) => ({ ...acc, [family.familyId]: family.familyGuid }), {})
          const familyGuids = newValue.parsedData.map(row => familyIdMap[row[0]]).filter(familyGuid => familyGuid)
          const info = [`Uploaded ${familyGuids.length} families`]
          if (newValue.parsedData.length !== familyGuids.length) {
            const missingFamilies = newValue.parsedData.filter(row => !familyIdMap[row[0]]).map(row => row[0])
            info.push(`Unable to find families with the following IDs: ${missingFamilies.join(', ')}`)
          }
          return { ...newValue, familyGuids, info }
        }
        return newValue
      }}
      onChange={(e, newValue) => {
        if (newValue.familyGuids) {
          onChange([...new Set([...value, ...newValue.familyGuids])])
        }
      }}
      clearTimeOut={0}
      auto
      returnParsedData
      dropzoneLabel="Drag-drop or click here to upload a list of family IDs"
    />
    <SelectableTableFormInput
      idField="familyGuid"
      defaultSortColumn={FAMILY_DISPLAY_NAME}
      columns={FAMILY_FIELDS}
      data={families}
      value={value.reduce((acc, key) => ({ ...acc, [key]: true }), {})}
      onChange={newValue => onChange(Object.keys(newValue).filter(key => newValue[key]))}
    />
  </div>

FamilySelectorField.propTypes = {
  value: PropTypes.array,
  families: PropTypes.array.isRequired,
  onChange: PropTypes.func,
}


const FORM_FIELDS = [
  { name: 'name', label: 'Name', validate: value => (value ? undefined : 'Name is required') },
  { name: 'description', label: 'Description' },
  {
    name: 'familyGuids',
    component: FamilySelectorField,
    validate: value => ((value && value.length) ? undefined : 'Families are required'),
    format: value => value || [],
  },
]

export const UpdateAnalysisGroup = ({ project, analysisGroup, onSubmit, projectFamiliesByGuid, iconOnly }) => {
  if (!project.canEdit) {
    return null
  }
  const title = `${analysisGroup ? 'Edit' : 'Create New'} Analysis Group`
  const buttonProps = analysisGroup ?
    { modalId: `editAnalysisGroup-${analysisGroup.analysisGroupGuid}`, initialValues: analysisGroup } :
    { modalId: `createAnalysisGroup-${project.projectGuid}`, initialValues: { projectGuid: project.projectGuid }, editIconName: 'plus' }

  const fields = [...FORM_FIELDS]
  fields[2].families = Object.values(projectFamiliesByGuid)

  return <UpdateButton
    modalTitle={title}
    buttonText={iconOnly ? null : title}
    onSubmit={onSubmit}
    formFields={fields}
    showErrorPanel
    {...buttonProps}
  />
}

UpdateAnalysisGroup.propTypes = {
  project: PropTypes.object,
  analysisGroup: PropTypes.object,
  iconOnly: PropTypes.bool,
  projectFamiliesByGuid: PropTypes.object,
  onSubmit: PropTypes.func,
}


export const DeleteAnalysisGroup = ({ project, analysisGroup, onSubmit, size, iconOnly, history }) => (
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
  project: getCurrentProject(state),
  projectFamiliesByGuid: getProjectFamiliesByGuid(state),
})

const mapDispatchToProps = {
  onSubmit: updateAnalysisGroup,
}

export const UpdateAnalysisGroupButton = connect(mapStateToProps, mapDispatchToProps)(UpdateAnalysisGroup)
export const DeleteAnalysisGroupButton = withRouter(connect(mapStateToProps, mapDispatchToProps)(DeleteAnalysisGroup))

