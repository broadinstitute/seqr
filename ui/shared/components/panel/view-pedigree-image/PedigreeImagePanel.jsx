import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Icon, Message } from 'semantic-ui-react'
import styled from 'styled-components'

import { RECEIVE_DATA } from 'redux/rootReducer'
import { closeModal } from 'redux/utils/modalReducer'
import Modal from '../../modal/Modal'
import { XHRUploaderWithEvents } from '../../form/XHRUploaderField'
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
    const { familyId, familyGuid } = this.props.family
    return (
      <Modal
        title={`Upload Pedigree for Family ${familyId}`}
        modalName={this.modalId}
        trigger={<ButtonLink content="Add Pedigree" icon="plus" labelPosition="right" />}
      >
        <XHRUploaderWithEvents
          onUploadFinished={this.onFinished}
          url={`/api/family/${familyGuid}/update_pedigree_image`}
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
      dispatch({ type: RECEIVE_DATA, updatesById: responseJson })
      dispatch(closeModal(modalId))
    },
  }
}


const EditPedigreeImageButton = connect(null, mapDispatchToProps)(BaseEditPedigreeImageButton)

const PedigreeImagePanel = (props) => {
  if (!props.family.pedigreeImage) {
    return props.isEditable && !props.compact ? <EditPedigreeImageButton family={props.family} /> : null
  }
  const image = <PedigreeImage
    src={props.family.pedigreeImage}
    disablePedigreeZoom={props.disablePedigreeZoom}
    compact={props.compact}
  />
  return props.disablePedigreeZoom ? image : (
    <Modal
      modalName={`Pedigree-${props.family.familyGuid}`}
      title={`Family ${props.family.displayName}`}
      trigger={
        <span>
          {props.compact && `(${props.family.individualGuids.length}) `} <a role="button" tabIndex="0">{image}</a>
        </span>
      }
    >
      <img src={props.family.pedigreeImage} alt="pedigree" style={{ maxHeight: '250px', maxWidth: '400px' }} /><br />
      <a href={props.family.pedigreeImage} target="_blank">
        <Icon name="zoom" /> Original Size
      </a>
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
