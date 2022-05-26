import React from 'react'
import createDecorator from 'final-form-calculate'
import PropTypes from 'prop-types'
import { withRouter } from 'react-router-dom'
import { connect } from 'react-redux'

import UpdateButton from 'shared/components/buttons/UpdateButton'
import DeleteButton from 'shared/components/buttons/DeleteButton'
import FileUploadField from 'shared/components/form/XHRUploaderField'
import PedigreeImagePanel from 'shared/components/panel/view-pedigree-image/PedigreeImagePanel'
import { SelectableTableFormInput } from 'shared/components/table/DataTable'
import {
  FAMILY_DISPLAY_NAME,
  FAMILY_FIELD_PEDIGREE,
  FAMILY_FIELD_DESCRIPTION,
} from 'shared/utils/constants'

import { updateAnalysisGroup } from '../reducers'
import { getProjectFamiliesByGuid, getCurrentProject } from '../selectors'

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

const normalizeFamilyUpload = allFamilies => (newValue) => {
  if (newValue.errors) {
    return { ...newValue, info: newValue.errors, errors: [] }
  }

  if (newValue.parsedData) {
    const familyIdMap = allFamilies.reduce(
      (acc, family) => ({ ...acc, [family.familyId]: family.familyGuid }), {},
    )
    const familyGuids = newValue.parsedData.map(row => familyIdMap[row[0]]).filter(familyGuid => familyGuid)

    if (familyGuids) {
      const info = [`Uploaded ${familyGuids.length} families`]
      if (newValue.parsedData.length !== familyGuids.length) {
        const missingFamilies = newValue.parsedData.filter(row => !familyIdMap[row[0]]).map(row => row[0])
        info.push(`Unable to find families with the following IDs: ${missingFamilies.join(', ')}`)
      }
      return { ...newValue, familyGuids, info }
    }
  }

  return newValue
}

const UPLOADED_FAMILIES_FIELD = 'uploadedFamilyIds'
const FAMILY_GUIDS_FIELD = 'familyGuids'

const FamilyFileUploadField = React.memo(({ onChange, data }) => (
  <FileUploadField
    name={UPLOADED_FAMILIES_FIELD}
    parse={normalizeFamilyUpload(data)}
    onChange={onChange}
    returnParsedData
    dropzoneLabel="Drag-drop or click here to upload a list of family IDs"
  />
))

FamilyFileUploadField.propTypes = {
  onChange: PropTypes.func,
  data: PropTypes.arrayOf(PropTypes.object),
}

const mapTableInputStateToProps = state => ({
  data: Object.values(getProjectFamiliesByGuid(state)),
})

const FORM_FIELDS = [
  { name: 'name', label: 'Name', validate: value => (value ? undefined : 'Name is required') },
  { name: 'description', label: 'Description' },
  {
    name: UPLOADED_FAMILIES_FIELD,
    key: 'familyUpload',
    component: connect(mapTableInputStateToProps)(FamilyFileUploadField),
  },
  {
    name: FAMILY_GUIDS_FIELD,
    key: 'familyTable',
    idField: 'familyGuid',
    defaultSortColumn: FAMILY_DISPLAY_NAME,
    columns: FAMILY_FIELDS,
    component: connect(mapTableInputStateToProps)(SelectableTableFormInput),
    validate: value => ((value && value.length) ? undefined : 'Families are required'),
    format: value => (value || []).reduce((acc, key) => ({ ...acc, [key]: true }), {}),
    parse: value => Object.keys(value).filter(key => value[key]),
  },
]

const DECORATORS = [
  createDecorator({
    field: UPLOADED_FAMILIES_FIELD,
    updates: {
      [FAMILY_GUIDS_FIELD]: (uploadedFamiliesValue, allValues) => ([
        ...new Set([...(allValues[FAMILY_GUIDS_FIELD] || []), ...(uploadedFamiliesValue[FAMILY_GUIDS_FIELD] || [])]),
      ]),
    },
  }),
]

export const UpdateAnalysisGroup = React.memo(({ project, analysisGroup, onSubmit, iconOnly }) => {
  if (!project.canEdit) {
    return null
  }
  const title = `${analysisGroup ? 'Edit' : 'Create New'} Analysis Group`
  return (
    <UpdateButton
      modalTitle={title}
      modalId={
        analysisGroup ? `editAnalysisGroup-${analysisGroup.analysisGroupGuid}` :
          `createAnalysisGroup-${project.projectGuid}`
      }
      editIconName={analysisGroup ? null : 'plus'}
      buttonText={iconOnly ? null : title}
      onSubmit={onSubmit}
      formFields={FORM_FIELDS}
      showErrorPanel
      initialValues={analysisGroup}
      decorators={DECORATORS}
    />
  )
})

UpdateAnalysisGroup.propTypes = {
  project: PropTypes.object,
  analysisGroup: PropTypes.object,
  iconOnly: PropTypes.bool,
  onSubmit: PropTypes.func,
}

const mapUpdateStateToProps = state => ({
  project: getCurrentProject(state),
})

const mapDispatchToProps = {
  onSubmit: updateAnalysisGroup,
}

export const UpdateAnalysisGroupButton = connect(mapUpdateStateToProps, mapDispatchToProps)(UpdateAnalysisGroup)

const navigateProjectPage = (history, projectGuid) => () => history.push(`/project/${projectGuid}/project_page`)

export const DeleteAnalysisGroup = React.memo(({ project, analysisGroup, onSubmit, size, iconOnly, history }) => (
  project.canEdit ? (
    <DeleteButton
      initialValues={analysisGroup}
      onSubmit={onSubmit}
      confirmDialog={
        <div className="content">
          Are you sure you want to delete &nbsp;
          <b>{analysisGroup.name}</b>
        </div>
      }
      buttonText={iconOnly ? null : 'Delete Analysis Group'}
      size={size}
      onSuccess={navigateProjectPage(history, project.projectGuid)}
    />
  ) : null
))

DeleteAnalysisGroup.propTypes = {
  onSubmit: PropTypes.func,
  project: PropTypes.object,
  analysisGroup: PropTypes.object,
  iconOnly: PropTypes.bool,
  size: PropTypes.string,
  history: PropTypes.object,
}

const mapDeleteStateToProps = state => ({
  project: getCurrentProject(state),
})

export const DeleteAnalysisGroupButton = withRouter(
  connect(mapDeleteStateToProps, mapDispatchToProps)(DeleteAnalysisGroup),
)
