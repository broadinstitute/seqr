import React from 'react'
import createDecorator from 'final-form-calculate'
import PropTypes from 'prop-types'
import { withRouter } from 'react-router-dom'
import { connect } from 'react-redux'

import { getUser } from 'redux/selectors'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import DeleteButton from 'shared/components/buttons/DeleteButton'
import { Multiselect } from 'shared/components/form/Inputs'
import FileUploadField from 'shared/components/form/XHRUploaderField'
import PedigreeImagePanel from 'shared/components/panel/view-pedigree-image/PedigreeImagePanel'
import { SelectableTableFormInput } from 'shared/components/table/DataTable'
import {
  FAMILY_DISPLAY_NAME,
  FAMILY_FIELD_PEDIGREE,
  FAMILY_FIELD_DESCRIPTION,
  CATEGORY_FAMILY_FILTERS,
  FAMILY_FIELD_NAME_LOOKUP,
  ANVIL_FIELDS,
  GREGOR_FINDING_TAG_NAME,
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

const NAME_FIELD = { name: 'name', label: 'Name', validate: value => (value ? undefined : 'Name is required') }

const FORM_FIELDS = [
  NAME_FIELD,
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

const ANVIL_FORM_FIELDS = [
  ...FORM_FIELDS.slice(0, 2),
  ...ANVIL_FIELDS.map(({ validate, ...field }) => ({
    ...field,
    labelHelp: `Add an AnVIL workspace to control access for this subset of families. Accounts with access to this 
    workspace will gain access  to thes families even if they have no access t the rest of the project.`,
  })),
  ...FORM_FIELDS.slice(2),
]

const DYNAMIC_FORM_FIELDS = [
  NAME_FIELD,
  ...Object.entries(CATEGORY_FAMILY_FILTERS).map(([category, options], i) => ({
    name: `criteria.${category}`,
    label: `Criteria: ${FAMILY_FIELD_NAME_LOOKUP[category]}`,
    options,
    component: Multiselect,
    includeCategories: true,
    color: 'blue',
    validate: i === 0 ? (value, allValues) => (allValues.criteria ? undefined : 'At least one criteria is required') : null,
  })),
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

const canUpdateGroup = (project, analysisGroup, user) => (
  project.canEdit && (!analysisGroup?.analysisGroupGuid || analysisGroup.projectGuid) && (
    !analysisGroup?.workspaceNamespace || user?.isPm
  )
)

export const UpdateAnalysisGroup = React.memo(({ project, user, analysisGroup, onSubmit, iconOnly, createDynamic }) => {
  if (!canUpdateGroup(project, analysisGroup, user)) {
    return null
  }
  const isDynamic = !!analysisGroup?.criteria || createDynamic
  const title = `${analysisGroup ? 'Edit' : 'Create New'} ${isDynamic ? 'Dynamic ' : ''}Analysis Group`
  const entityName = `${isDynamic ? 'Dynamic' : ''}AnalysisGroup`

  let formFields = FORM_FIELDS
  if (isDynamic) {
    formFields = DYNAMIC_FORM_FIELDS
  } else if (user.isPm && (project.isAnalystProject || project.variantTagTypes?.some(
    ({ name }) => name === GREGOR_FINDING_TAG_NAME,
  ))) {
    formFields = ANVIL_FORM_FIELDS
  }

  return (
    <UpdateButton
      modalTitle={title}
      modalId={
        analysisGroup ? `edit${entityName}-${analysisGroup.analysisGroupGuid}` :
          `create${entityName}-${project.projectGuid}`
      }
      editIconName={analysisGroup ? null : 'plus'}
      buttonText={iconOnly ? null : title}
      onSubmit={onSubmit}
      formFields={formFields}
      showErrorPanel
      initialValues={analysisGroup}
      decorators={isDynamic ? null : DECORATORS}
    />
  )
})

UpdateAnalysisGroup.propTypes = {
  project: PropTypes.object,
  user: PropTypes.object,
  analysisGroup: PropTypes.object,
  iconOnly: PropTypes.bool,
  createDynamic: PropTypes.bool,
  onSubmit: PropTypes.func,
}

const mapUpdateStateToProps = state => ({
  project: getCurrentProject(state),
  user: getUser(state),
})

const mapDispatchToProps = {
  onSubmit: updateAnalysisGroup,
}

export const UpdateAnalysisGroupButton = connect(mapUpdateStateToProps, mapDispatchToProps)(UpdateAnalysisGroup)

const navigateProjectPage = (history, projectGuid) => () => history.push(`/project/${projectGuid}/project_page`)

export const DeleteAnalysisGroup = React.memo(({ project, analysisGroup, onSubmit, size, iconOnly, history }) => (
  canUpdateGroup(project, analysisGroup) ? (
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
