import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Icon, Message, Segment, Table } from 'semantic-ui-react'
import styled from 'styled-components'

import { updateFamily, RECEIVE_DATA } from 'redux/rootReducer'
import { closeModal } from 'redux/utils/modalReducer'
import DeleteButton from '../../buttons/DeleteButton'
import Modal from '../../modal/Modal'
import { XHRUploaderWithEvents } from '../../form/XHRUploaderField'
import { ButtonLink, NoBorderTable } from '../../StyledComponents'

const UploadedPedigreeImage = styled.img.attrs({ alt: 'pedigree' })`
  max-height: ${props => props.maxHeight};
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

const EditPedigreeImageButton = connect(null, mapDispatchToProps)(BaseEditPedigreeImageButton)

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

const DeletePedigreeImageButton = connect(null, mapDeleteDispatchToProps)(BaseDeletePedigreeImageButton)

const MIN_INDIVS_PER_PEDIGREE = 2

const PedigreeImage = ({ family, ...props }) => (
  family.pedigreeImage ? <UploadedPedigreeImage src={family.pedigreeImage} {...props} /> : 'PLACEHOLDER'
)

PedigreeImage.propTypes = {
  family: PropTypes.object.isRequired,
}

const PedigreeImagePanel = React.memo(({ family, isEditable, compact, disablePedigreeZoom }) => {
  const image = <PedigreeImage
    family={family}
    disablePedigreeZoom={disablePedigreeZoom}
    maxHeight={compact ? '35px' : '150px'}
  />
  if (disablePedigreeZoom) {
    return image
  }

  const modalId = `Pedigree-${family.familyGuid}`
  const numIndivs = family.individualGuids.length
  return (
    <Modal
      modalName={modalId}
      title={`Family ${family.displayName}`}
      trigger={
        <span>
          {compact && numIndivs >= MIN_INDIVS_PER_PEDIGREE && `(${numIndivs}) `} {image}
        </span>
      }
    >
      <Segment basic textAlign="center">
        <PedigreeImage family={family} disablePedigreeZoom maxHeight="250px" /><br />
      </Segment>
      <NoBorderTable basic="very" compact="very" collapsing>
        <Table.Body>
          <Table.Row>
            {family.pedigreeImage &&
              <Table.Cell>
                <a key="zoom" href={family.pedigreeImage} target="_blank">Original Size <Icon name="zoom" /></a>
              </Table.Cell>
            }
            {isEditable && <Table.Cell><EditPedigreeImageButton key="upload" family={family} /></Table.Cell>}
            {isEditable && family.pedigreeImage &&
              <Table.Cell><DeletePedigreeImageButton familyGuid={family.familyGuid} modalId={modalId} /></Table.Cell>
            }
          </Table.Row>
        </Table.Body>
      </NoBorderTable>
    </Modal>
  )
})

PedigreeImagePanel.propTypes = {
  family: PropTypes.object.isRequired,
  disablePedigreeZoom: PropTypes.bool,
  compact: PropTypes.bool,
  isEditable: PropTypes.bool,
}

export default PedigreeImagePanel
