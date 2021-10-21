import React from 'react'
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

const parseFamilyGuids = (newValue, previousValue, allValues) => {
  const parsed = {}
  if (newValue.parsedData && newValue.uploadedFileId !== (previousValue || {}).uploadedFileId) {
    parsed.familyIdMap = allValues.allFamilies.reduce(
      (acc, family) => ({ ...acc, [family.familyId]: family.familyGuid }), {},
    )
    parsed.familyGuids = newValue.parsedData.map(row => parsed.familyIdMap[row[0]]).filter(familyGuid => familyGuid)
  }
  return parsed
}

const normalizeFamilyUpload = (newValue, previousValue, allValues) => {
  if (newValue.errors) {
    return { ...newValue, info: newValue.errors, errors: [] }
  }

  const { familyGuids, familyIdMap } = parseFamilyGuids(newValue, previousValue, allValues)
  if (familyGuids) {
    const info = [`Uploaded ${familyGuids.length} families`]
    if (newValue.parsedData.length !== familyGuids.length) {
      const missingFamilies = newValue.parsedData.filter(row => !familyIdMap[row[0]]).map(row => row[0])
      info.push(`Unable to find families with the following IDs: ${missingFamilies.join(', ')}`)
    }
    return { ...newValue, familyGuids, info }
  }

  return newValue
}

const FamilyFileUploadField = React.memo(({ onChange }) => (
  <FileUploadField
    name="uploadedFamilyIds"
    normalize={normalizeFamilyUpload}
    onChange={onChange}
    clearTimeOut={0}
    auto
    returnParsedData
    dropzoneLabel="Drag-drop or click here to upload a list of family IDs"
  />
))

FamilyFileUploadField.propTypes = {
  onChange: PropTypes.func,
}

const mapTableInputStateToProps = state => ({
  data: Object.values(getProjectFamiliesByGuid(state)),
})

const FORM_FIELDS = [
  { name: 'name', label: 'Name', validate: value => (value ? undefined : 'Name is required') },
  { name: 'description', label: 'Description' },
  {
    name: 'familyGuids',
    key: 'familyUpload',
    component: FamilyFileUploadField,
    normalize: (newValue, previousValue, allValues) => {
      const { familyGuids } = parseFamilyGuids(newValue, previousValue, allValues)
      return [...new Set([...(previousValue || []), ...(familyGuids || [])])]
    },
  },
  {
    name: 'familyGuids',
    key: 'familyTable',
    idField: 'familyGuid',
    defaultSortColumn: FAMILY_DISPLAY_NAME,
    columns: FAMILY_FIELDS,
    component: connect(mapTableInputStateToProps)(SelectableTableFormInput),
    validate: value => ((value && value.length) ? undefined : 'Families are required'),
    format: value => (value || []).reduce((acc, key) => ({ ...acc, [key]: true }), {}),
    normalize: value => Object.keys(value).filter(key => value[key]),
  },
]

export const UpdateAnalysisGroup = React.memo(({ project, analysisGroup, initialValues, onSubmit, iconOnly }) => {
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
      initialValues={initialValues}
    />
  )
})

UpdateAnalysisGroup.propTypes = {
  project: PropTypes.object,
  analysisGroup: PropTypes.object,
  iconOnly: PropTypes.bool,
  initialValues: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapUpdateStateToProps = (state, ownProps) => {
  const project = getCurrentProject(state)
  const initialValues = ownProps.analysisGroup ? ownProps.analysisGroup : { projectGuid: project.projectGuid }
  return {
    initialValues: { ...initialValues, allFamilies: Object.values(getProjectFamiliesByGuid(state)) },
    project,
  }
}

const mapDispatchToProps = {
  onSubmit: ({ allFamilies, ...values }) => updateAnalysisGroup(values),
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
