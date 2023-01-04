import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Loader } from 'semantic-ui-react'

import { updateFamily } from 'redux/rootReducer'
import { RECEIVE_DATA } from 'redux/utils/reducerUtils'
import { closeModal } from 'redux/utils/modalReducer'
import DeleteButton from '../../buttons/DeleteButton'
import DispatchRequestButton from '../../buttons/DispatchRequestButton'
import Modal from '../../modal/Modal'
import { ButtonLink } from '../../StyledComponents'

const XHRUploaderWithEvents = React.lazy(() => import('../../form/XHRUploaderWithEvents'))
const PhiWarningUploadField = React.lazy(() => import('../../form/PhiWarningUploadField'))

const getModalId = family => `uploadPedigree-${family.familyGuid}`

const BaseEditPedigreeImageButton = ({ family, onSuccess }) => (
  <Modal
    title={`Upload Pedigree for Family ${family.familyId}`}
    modalName={getModalId(family)}
    trigger={<ButtonLink content="Upload New Image" icon="upload" labelPosition="right" />}
  >
    <React.Suspense fallback={<Loader />}>
      <PhiWarningUploadField>
        <XHRUploaderWithEvents
          onUploadFinished={onSuccess}
          url={`/api/family/${family.familyGuid}/update_pedigree_image`}
          clearTimeOut={0}
          auto
          maxFiles={1}
          dropzoneLabel="Drag and drop or click to upload pedigree image"
          showError
        />
      </PhiWarningUploadField>
    </React.Suspense>
  </Modal>
)

BaseEditPedigreeImageButton.propTypes = {
  family: PropTypes.object,
  onSuccess: PropTypes.func,
}

const mapDispatchToProps = (dispatch, ownProps) => ({
  onSuccess: (responseJson) => {
    dispatch({ type: RECEIVE_DATA, updatesById: { familiesByGuid: responseJson } })
    dispatch(closeModal(getModalId(ownProps.family)))
  },
})

export const EditPedigreeImageButton = connect(null, mapDispatchToProps)(BaseEditPedigreeImageButton)

const BaseDeletePedigreeImageButton = React.memo(({ onSubmit, onSuccess }) => (
  <DeleteButton
    onSubmit={onSubmit}
    onSuccess={onSuccess}
    confirmDialog="Are you sure you want to delete the pedigree image for this family?"
    buttonText="Delete Pedigree Image"
  />
))

BaseDeletePedigreeImageButton.propTypes = {
  onSubmit: PropTypes.func,
  onSuccess: PropTypes.func,
}

const mapDeleteDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: () => dispatch(updateFamily({ familyField: 'pedigree_image', familyGuid: ownProps.familyGuid })),
  onSuccess: () => dispatch(closeModal(ownProps.modalId)),
})

export const DeletePedigreeImageButton = connect(null, mapDeleteDispatchToProps)(BaseDeletePedigreeImageButton)

const BaseSavePedigreeDatasetButton = React.memo(({ onSubmit, onSuccess }) => (
  <DispatchRequestButton
    onSubmit={onSubmit}
    onSuccess={onSuccess}
    icon="save"
    size="huge"
    confirmDialog="Are you sure you want to save this pedigree?"
  />
))

BaseSavePedigreeDatasetButton.propTypes = {
  onSubmit: PropTypes.func,
  onSuccess: PropTypes.func,
}

const mapSaveDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: () => dispatch(
    updateFamily({ pedigreeDataset: ownProps.getPedigreeDataset(), familyGuid: ownProps.familyGuid }),
  ),
  onSuccess: () => dispatch(closeModal(ownProps.modalId)),
})

export const SavePedigreeDatasetButton = connect(null, mapSaveDispatchToProps)(BaseSavePedigreeDatasetButton)
