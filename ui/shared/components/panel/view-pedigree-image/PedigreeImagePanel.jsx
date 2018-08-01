import React from 'react'
import PropTypes from 'prop-types'
import { Icon } from 'semantic-ui-react'
import styled from 'styled-components'

import Modal from '../../modal/Modal'

const PedigreeImage = styled.img.attrs({ alt: 'pedigree' })`
  max-height: ${props => (props.compact ? '35px' : '100px')};
  max-width: 150px;
  vertical-align: top;
  cursor: ${props => (props.disablePedigreeZoom ? 'auto' : 'zoom-in')};
`

const PedigreeImagePanel = (props) => {
  if (!props.family.pedigreeImage) {
    return null
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
}

export default PedigreeImagePanel
