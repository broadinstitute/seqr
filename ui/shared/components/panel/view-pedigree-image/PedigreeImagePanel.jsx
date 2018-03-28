import React from 'react'
import PropTypes from 'prop-types'
import { Icon } from 'semantic-ui-react'

import Modal from '../../modal/Modal'

const PedigreeImagePanel = props => (
  props.family.pedigreeImage ?
    <Modal
      title={`Family ${props.family.displayName}`}
      trigger={
        <a role="button" tabIndex="0">
          <img
            src={props.family.pedigreeImage}
            alt="pedigree"
            style={{ maxHeight: '100px', maxWidth: '150px', verticalAlign: 'top', cursor: 'zoom-in' }}
          />
        </a>
      }
    >
      <center>
        <img src={props.family.pedigreeImage} alt="pedigree" style={{ maxHeight: '250px', maxWidth: '400px' }} /><br />
        <a href={props.family.pedigreeImage} target="_blank" rel="noopener noreferrer">
          <Icon name="zoom" /> Original Size
        </a>
      </center>
    </Modal> : null
)

PedigreeImagePanel.propTypes = {
  family: PropTypes.object.isRequired,
}

export default PedigreeImagePanel
