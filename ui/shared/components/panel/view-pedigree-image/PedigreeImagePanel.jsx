import React from 'react'
import PropTypes from 'prop-types'
import { Icon } from 'semantic-ui-react'

import Modal from '../../modal/Modal'

const PedigreeImagePanel = (props) => {
  if (!props.family.pedigreeImage) {
    return null
  }
  const image = <img
    src={props.family.pedigreeImage}
    alt="pedigree"
    style={{ maxHeight: '100px', maxWidth: '150px', verticalAlign: 'top', cursor: props.disablePedigreeZoom ? 'auto' : 'zoom-in' }}
  />
  return props.disablePedigreeZoom ? image : (
    <Modal
      modalName={`Pedigree-${props.family.familyGuid}`}
      title={`Family ${props.family.displayName}`}
      trigger={<a role="button" tabIndex="0">{image}</a>}
    >
      <center>
        <img src={props.family.pedigreeImage} alt="pedigree" style={{ maxHeight: '250px', maxWidth: '400px' }} /><br />
        <a href={props.family.pedigreeImage} target="_blank" rel="noopener noreferrer">
          <Icon name="zoom" /> Original Size
        </a>
      </center>
    </Modal>
  )
}

PedigreeImagePanel.propTypes = {
  family: PropTypes.object.isRequired,
  disablePedigreeZoom: PropTypes.bool,
}

export default PedigreeImagePanel
