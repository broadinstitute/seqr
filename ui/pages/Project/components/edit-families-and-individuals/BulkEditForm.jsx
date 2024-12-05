import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getUser } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'

import FormWrapper from 'shared/components/form/FormWrapper'
import BulkUploadForm from 'shared/components/form/BulkUploadForm'
import {
  FILE_FIELD_NAME,
  FILE_FORMATS,
  INDIVIDUAL_CORE_EXPORT_DATA,
  INDIVIDUAL_ID_EXPORT_DATA,
} from 'shared/utils/constants'
import { FAMILY_BULK_EDIT_EXPORT_DATA, INDIVIDUAL_DETAIL_EXPORT_DATA, INDIVIDUAL_INTERNAL_EXPORT_DATA } from '../../constants'
import { loadIndividuals, updateFamilies, updateIndividuals, updateIndividualsMetadata } from '../../reducers'
import {
  getCurrentProject,
  getEntityExportConfig,
  getIndivdualsLoading,
  getProjectAnalysisGroupFamiliesByGuid,
  getProjectAnalysisGroupIndividualsByGuid,
} from '../../selectors'

const FAM_UPLOAD_FORMATS = [].concat(FILE_FORMATS)
FAM_UPLOAD_FORMATS[1] = { ...FAM_UPLOAD_FORMATS[1], formatLinks: [...FAM_UPLOAD_FORMATS[1].formatLinks, { href: 'https://www.cog-genomics.org/plink2/formats#fam', linkExt: 'fam' }] }

const mapStateToProps = (state, ownProps) => {
  const project = getCurrentProject(state)
  const fields = ownProps.requiredFields.concat(ownProps.optionalFields)
  return {
    project,
    exportConfig: {
      getRawData: state2 => Object.values(
        (ownProps.getRawData || getProjectAnalysisGroupIndividualsByGuid)(state2, ownProps),
      ),
      ...getEntityExportConfig({ projectName: project.name, fileName: ownProps.name, fields }),
    },
    blankExportConfig: {
      rawData: [],
      ...getEntityExportConfig({ projectName: project.name, fileName: 'template', fields }),
    },
  }
}

const BulkContent = connect(mapStateToProps)(BulkUploadForm)

const submitForm = onSubmit => values => onSubmit(values[FILE_FIELD_NAME])

const EditBulkForm = React.memo(({ name, modalName, onSubmit, ...props }) => (
  <FormWrapper
    modalName={modalName}
    onSubmit={submitForm(onSubmit)}
    confirmCloseIfNotSaved
    closeOnSuccess
    showErrorPanel
    liveValidate
    size="small"
  >
    <BulkContent name={name} {...props} />
  </FormWrapper>
))

EditBulkForm.propTypes = {
  name: PropTypes.string.isRequired,
  modalName: PropTypes.string.isRequired,
  onSubmit: PropTypes.func.isRequired,
}

const FAMILY_ID_EXPORT_DATA = FAMILY_BULK_EDIT_EXPORT_DATA.slice(0, 1)
const FAMILY_EXPORT_DATA = FAMILY_BULK_EDIT_EXPORT_DATA.slice(1)
const FAMILY_CORE_EXPORT_DATA = FAMILY_BULK_EDIT_EXPORT_DATA.slice(1, 5)

const FamiliesBulkForm = React.memo(({ user, ...props }) => (
  <EditBulkForm
    name="families"
    actionDescription="bulk edit families"
    details={
      <div>
        The Family ID in the table must match those of an existing family in the project.
        To edit an existing families&apos;s ID include a &nbsp;
        <b>Previous Family ID</b>
        &nbsp; column.
      </div>
    }
    requiredFields={FAMILY_ID_EXPORT_DATA}
    optionalFields={user.isAnalyst ? FAMILY_EXPORT_DATA : FAMILY_CORE_EXPORT_DATA}
    uploadFormats={FILE_FORMATS}
    getRawData={getProjectAnalysisGroupFamiliesByGuid}
    templateLinkContent="current families"
    {...props}
  />
))

FamiliesBulkForm.propTypes = {
  user: PropTypes.object,
}

const mapFamiliesStateToProps = state => ({
  user: getUser(state),
})

const mapFamiliesDispatchToProps = {
  onSubmit: updateFamilies,
}

export const EditFamiliesBulkForm = connect(mapFamiliesStateToProps, mapFamiliesDispatchToProps)(FamiliesBulkForm)

const INDIVIDUAL_BULK_UPDATE_EXPORT_DATA = [...INDIVIDUAL_CORE_EXPORT_DATA, ...INDIVIDUAL_INTERNAL_EXPORT_DATA]

const IndividualsBulkForm = React.memo(({ user, load, loading, ...props }) => (
  <DataLoader load={load} loading={loading} content>
    <EditBulkForm
      name="individuals"
      actionDescription="bulk-add or edit individuals"
      details={
        <div>
          If the Family ID and Individual ID in the table match those of an existing individual in the project,
          the matching individual&apos;s data will be updated with values from the table. Otherwise, a new individual
          will be created. To edit an existing individual&apos;s ID include a &nbsp;
          <b>Previous Individual ID</b>
          &nbsp; column.
        </div>
      }
      requiredFields={INDIVIDUAL_ID_EXPORT_DATA}
      optionalFields={user.isAnalyst ? INDIVIDUAL_BULK_UPDATE_EXPORT_DATA : INDIVIDUAL_CORE_EXPORT_DATA}
      uploadFormats={FAM_UPLOAD_FORMATS}
      {...props}
    />
  </DataLoader>
))

IndividualsBulkForm.propTypes = {
  user: PropTypes.object,
  load: PropTypes.func,
  loading: PropTypes.bool,
}

const mapIndividualsStateToProps = state => ({
  user: getUser(state),
  loading: getIndivdualsLoading(state),
})

const mapIndividualsDispatchToProps = {
  load: loadIndividuals,
  onSubmit: updateIndividuals,
}

export const EditIndividualsBulkForm = connect(
  mapIndividualsStateToProps, mapIndividualsDispatchToProps,
)(IndividualsBulkForm)

const IndividualMetadataBulkForm = React.memo(({ load, loading, ...props }) => (
  <DataLoader load={load} loading={loading} content>
    <EditBulkForm
      name="individuals_metadata"
      actionDescription="edit individual's metadata"
      details="Alternately, the table can have a single row per HPO term"
      requiredFields={INDIVIDUAL_ID_EXPORT_DATA}
      optionalFields={INDIVIDUAL_DETAIL_EXPORT_DATA}
      uploadFormats={FILE_FORMATS}
      {...props}
    />
  </DataLoader>
))

IndividualMetadataBulkForm.propTypes = {
  load: PropTypes.func,
  loading: PropTypes.bool,
}

const mapIndividualsMetadataStateToProps = state => ({
  loading: getIndivdualsLoading(state),
})

const mapIndividualMetadataDispatchToProps = {
  load: loadIndividuals,
  onSubmit: updateIndividualsMetadata,
}

export const EditIndividualMetadataBulkForm = connect(
  mapIndividualsMetadataStateToProps, mapIndividualMetadataDispatchToProps,
)(IndividualMetadataBulkForm)
