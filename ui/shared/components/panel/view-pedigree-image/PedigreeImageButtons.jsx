import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Message } from 'semantic-ui-react'

import { updateFamily, RECEIVE_DATA } from 'redux/rootReducer'
import { closeModal } from 'redux/utils/modalReducer'
import DeleteButton from '../../buttons/DeleteButton'
import DispatchRequestButton from '../../buttons/DispatchRequestButton'
import Modal from '../../modal/Modal'
import { XHRUploaderWithEvents } from '../../form/XHRUploaderField'
import { ButtonLink } from '../../StyledComponents'

class BaseEditPedigreeImageButton extends React.PureComponent {

  constructor(props) {
    super(props)
    this.state = { error: null }
    this.modalId = `uploadPedigree-${props.family.familyGuid}`
  }

  onFinished = xhr => (
    xhr.status === 200 ? this.props.onSuccess(JSON.parse(xhr.response), this.modalId) :
      this.setState({ error: `Error: ${xhr.statusText} (${xhr.status})` }))

  render() {
    const { family } = this.props
    return (
      <Modal
        title={`Upload Pedigree for Family ${family.familyId}`}
        modalName={this.modalId}
        trigger={<ButtonLink content="Upload New Image" icon="upload" labelPosition="right" />}
      >
        <XHRUploaderWithEvents
          onUploadFinished={this.onFinished}
          url={`/api/family/${family.familyGuid}/update_pedigree_image`}
          clearTimeOut={0}
          auto
          maxFiles={1}
          dropzoneLabel="Drag and drop or click to upload pedigree image"
        />
        {this.state.error && <Message error content={this.state.error} />}
      </Modal>
    )
  }
}

BaseEditPedigreeImageButton.propTypes = {
  family: PropTypes.object,
  onSuccess: PropTypes.func,
}

const mapDispatchToProps = (dispatch) => {
  return {
    onSuccess: (responseJson, modalId) => {
      dispatch({ type: RECEIVE_DATA, updatesById: { familiesByGuid: responseJson } })
      dispatch(closeModal(modalId))
    },
  }
}

export const EditPedigreeImageButton = connect(null, mapDispatchToProps)(BaseEditPedigreeImageButton)

const BaseDeletePedigreeImageButton = React.memo(({ onSubmit, onSuccess }) =>
  <DeleteButton
    onSubmit={onSubmit}
    onSuccess={onSuccess}
    confirmDialog="Are you sure you want to delete the pedigree image for this family?"
    buttonText="Delete Pedigree Image"
  />,
)

BaseDeletePedigreeImageButton.propTypes = {
  onSubmit: PropTypes.func,
  onSuccess: PropTypes.func,
}

const mapDeleteDispatchToProps = (dispatch, ownProps) => {
  return {
    onSubmit: () => {
      return dispatch(updateFamily({ familyField: 'pedigree_image', familyGuid: ownProps.familyGuid }))
    },
    onSuccess: () => {
      dispatch(closeModal(ownProps.modalId))
    },
  }
}

export const DeletePedigreeImageButton = connect(null, mapDeleteDispatchToProps)(BaseDeletePedigreeImageButton)


const BaseSavePedigreeDatasetButton = React.memo(({ onSubmit, onSuccess }) =>
  <DispatchRequestButton
    onSubmit={onSubmit}
    onSuccess={onSuccess}
    icon="save"
    size="huge"
    confirmDialog="Are you sure you want to save this pedigree?"
  />,
)

BaseSavePedigreeDatasetButton.propTypes = {
  onSubmit: PropTypes.func,
  onSuccess: PropTypes.func,
}

const mapSaveDispatchToProps = (dispatch, ownProps) => {
  return {
    onSubmit: () => {
      return dispatch(updateFamily({ pedigreeDataset: ownProps.getPedigreeDataset(), familyGuid: ownProps.familyGuid }))
    },
    onSuccess: () => {
      dispatch(closeModal(ownProps.modalId))
    },
  }
}

export const SavePedigreeDatasetButton = connect(null, mapSaveDispatchToProps)(BaseSavePedigreeDatasetButton)
