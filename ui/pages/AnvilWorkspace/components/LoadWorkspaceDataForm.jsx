import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { FILE_FIELD_NAME, PROJECT_DESC_FIELDS, FAMILY_FIELD_ID, INDIVIDUAL_FIELD_ID } from 'shared/utils/constants'
import { BaseBulkContent, BASE_UPLOAD_FORMATS } from 'pages/Project/components/edit-families-and-individuals/BulkEditForm'
import { INDIVIDUAL_CORE_EXPORT_DATA, INDIVIDUAL_ID_EXPORT_DATA } from 'pages/Project/constants'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { VerticalSpacer } from 'shared/components/Spacers'

const StyledTitle = styled.h3`
  text-align: center;
  height: 40px;
  margin: 0 0 .28571429rem 0;
`

const StyledFieldDesc = styled.div`
  color: rgba(0,0,0,.87);
  font-size: .92857143em;
  font-weight: 700;
  margin: 0 0 .28571429rem 0;
`

const StyledField = styled.div`
  border: solid gray 1px;
  border-color: rgb(202, 202, 202);
  border-radius: .28571429rem;
`

const FIELD_DESCRIPTIONS = {
  [FAMILY_FIELD_ID]: 'Family ID of the individual',
  [INDIVIDUAL_FIELD_ID]: 'ID of the Individual (needs to match the VCF ids)',
}
const REQUIRED_FIELDS = INDIVIDUAL_ID_EXPORT_DATA.map(config => (
  { ...config, description: FIELD_DESCRIPTIONS[config.field] }))

const BLANK_EXPORT = {
  filename: 'individuals_template',
  rawData: [],
  headers: [...INDIVIDUAL_ID_EXPORT_DATA, ...INDIVIDUAL_CORE_EXPORT_DATA].map(config => config.header),
  processRow: val => val,
}

const UploadPedigreeField = React.memo(() =>
  <div>
    <StyledFieldDesc>
      Upload Pedigree Data
    </StyledFieldDesc>
    <StyledField>
      <BaseBulkContent
        blankExportConfig={BLANK_EXPORT}
        requiredFields={REQUIRED_FIELDS}
        optionalFields={INDIVIDUAL_CORE_EXPORT_DATA}
        uploadFormats={BASE_UPLOAD_FORMATS}
        actionDescription="load individual data from an AnVIL workspace to a new seqr project"
        url="/api/create_project_from_workspace/upload_individuals_table"
      />
      <VerticalSpacer height={10} />
    </StyledField>
  </div>,

)

const UPLOAD_PEDIGREE_FIELD = {
  name: FILE_FIELD_NAME,
  component: UploadPedigreeField,
}

const FORM_FIELDS = [PROJECT_DESC_FIELDS, UPLOAD_PEDIGREE_FIELD]

const LoadWorkspaceDataForm = React.memo(({ namespace, name }) =>
  <div>
    <StyledTitle>Load data to seqr from AnVIL Workspace &quot;{namespace}/{name}&quot;</StyledTitle>
    <ReduxFormWrapper
      form="loadWorkspaceData"
      modalName="loadWorkspaceData"
      onSubmit={values => console.log(values, namespace, name)}
      confirmCloseIfNotSaved
      closeOnSuccess
      showErrorPanel
      liveValidate
      size="small"
      fields={FORM_FIELDS}
    />
  </div>,
)

LoadWorkspaceDataForm.propTypes = {
  namespace: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
}

export default LoadWorkspaceDataForm
