import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Icon, Message, Segment } from 'semantic-ui-react'
import styled from 'styled-components'

import { updateFamily, RECEIVE_DATA } from 'redux/rootReducer'
import { closeModal } from 'redux/utils/modalReducer'
import DeleteButton from '../../buttons/DeleteButton'
import Modal from '../../modal/Modal'
import { XHRUploaderWithEvents } from '../../form/XHRUploaderField'
import { HorizontalSpacer } from '../../Spacers'
import { ButtonLink } from '../../StyledComponents'

const PedigreeImage = styled.img.attrs({ alt: 'pedigree' })`
  max-height: ${props => (props.compact ? '35px' : '150px')};
  max-width: 225px;
  vertical-align: top;
  cursor: ${props => (props.disablePedigreeZoom ? 'auto' : 'zoom-in')};
`

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
    const { family, buttonText } = this.props
    return (
      <Modal
        title={`Upload Pedigree for Family ${family.familyId}`}
        modalName={this.modalId}
        trigger={<ButtonLink content={buttonText} icon="upload" labelPosition="right" />}
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
  buttonText: PropTypes.string,
}

const mapDispatchToProps = (dispatch) => {
  return {
    onSuccess: (responseJson, modalId) => {
      dispatch({ type: RECEIVE_DATA, updatesById: { familiesByGuid: responseJson } })
      dispatch(closeModal(modalId))
    },
  }
}

const EditPedigreeImageButton = connect(null, mapDispatchToProps)(BaseEditPedigreeImageButton)

const BaseDeletePedigreeImageButton = ({ onSubmit, onSuccess }) =>
  <DeleteButton
    onSubmit={onSubmit}
    onSuccess={onSuccess}
    confirmDialog="Are you sure you want to delete the pedigree image for this family?"
    buttonText="Delete Pedigree Image"
  />

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

const DeletePedigreeImageButton = connect(null, mapDeleteDispatchToProps)(BaseDeletePedigreeImageButton)

const PedigreeImagePanel = (props) => {
  if (!props.family.pedigreeImage) {
    return props.isEditable && !props.compact ?
      <EditPedigreeImageButton family={props.family} buttonText="Upload Pedigree" /> : null
  }
  const image = <PedigreeImage
    src={props.family.pedigreeImage}
    disablePedigreeZoom={props.disablePedigreeZoom}
    compact={props.compact}
  />
  const modalId = `Pedigree-${props.family.familyGuid}`
  return props.disablePedigreeZoom ? image : (
    <Modal
      modalName={modalId}
      title={`Family ${props.family.displayName}`}
      trigger={
        <span>
          {props.compact && `(${props.family.individualGuids.length}) `} <a role="button" tabIndex="0">{image}</a>
        </span>
      }
    >
      <Segment basic textAlign="center">
        <img src={props.family.pedigreeImage} alt="pedigree" style={{ maxHeight: '250px' }} /><br />
      </Segment>
      <a href={props.family.pedigreeImage} target="_blank">
        Original Size <Icon name="zoom" />
      </a>
      <HorizontalSpacer width={20} />
      <EditPedigreeImageButton family={props.family} buttonText="Upload New Image" />
      <HorizontalSpacer width={20} />
      <DeletePedigreeImageButton familyGuid={props.family.familyGuid} modalId={modalId} />
    </Modal>
  )
}

PedigreeImagePanel.propTypes = {
  family: PropTypes.object.isRequired,
  disablePedigreeZoom: PropTypes.bool,
  compact: PropTypes.bool,
  isEditable: PropTypes.bool,
}

export default PedigreeImagePanel
