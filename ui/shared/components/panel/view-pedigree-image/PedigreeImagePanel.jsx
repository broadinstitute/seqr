import React from 'react'
import PropTypes from 'prop-types'
import { Icon, Segment, Table } from 'semantic-ui-react'
import styled from 'styled-components'
import { build as buildPedigeeJs } from 'pedigreejs/es/pedigree'
import { scale_to_fit as scalePedigreeToFit } from 'pedigreejs/es/zoom'

import Modal from '../../modal/Modal'
import { NoBorderTable, FontAwesomeIconsContainer } from '../../StyledComponents'
import { EditPedigreeImageButton, DeletePedigreeImageButton } from './PedigreeImageButtons'

const PED_IMAGE_SIZES = {
  small: { height: 35, width: 50 },
  medium: { height: 150, width: 250 },
  large: { height: 250, width: 350 },
}

const UploadedPedigreeImage = styled.img.attrs({ alt: 'pedigree' })`
  max-height: ${props => PED_IMAGE_SIZES[props.size].height}px;
  max-width: 225px;
  vertical-align: top;
  cursor: ${props => (props.disablePedigreeZoom ? 'auto' : 'zoom-in')};
`

const MIN_INDIVS_PER_PEDIGREE = 2

class PedigreeJs extends React.PureComponent {

  static propTypes = {
    family: PropTypes.object,
    size: PropTypes.string,
    disablePedigreeZoom: PropTypes.bool,
    isEditable: PropTypes.bool,
  }

  constructor(props) {
    super(props)
    this.containerId = `pedigreeJS-${props.family.familyGuid}-${props.size}`
  }

  render() {
    // TODO fix display in family label hover (i.e. saved variant page)
    return (
      <FontAwesomeIconsContainer>
        <div id={`${this.containerId}-buttons`} />
        <div id={this.containerId} />
      </FontAwesomeIconsContainer>)
  }

  componentDidMount() {
    const { size, disablePedigreeZoom, isEditable } = this.props
    const dataset = [
      { name: 'm21', sex: 'M', top_level: true },
      { name: 'f21', sex: 'F', top_level: true },
      { name: 'ch1', sex: 'F', mother: 'f21', father: 'm21', affected: true },
    ]
    const opts = {
      dataset,
      targetDiv: this.containerId,
      btn_target: `${this.containerId}-buttons`,
      edit: !!(disablePedigreeZoom && isEditable),
      background: '#fff',
      diseases: [{ type: 'affected', colour: '#111' }],
      labels: ['name'],
      zoomIn: 5,
      zoomOut: 5,
      store_type: 'array', // TODO remove?
      ...PED_IMAGE_SIZES[size],
    }
    const builtOpts = buildPedigeeJs(opts)
    scalePedigreeToFit(builtOpts)
  }
}


const PedigreeImage = ({ family, ...props }) => (
  family.pedigreeImage ?
    <UploadedPedigreeImage src={family.pedigreeImage} {...props} /> : <PedigreeJs family={family} {...props} />
)

PedigreeImage.propTypes = {
  family: PropTypes.object.isRequired,
}

const PedigreeImagePanel = React.memo(({ family, isEditable, compact, disablePedigreeZoom }) => {
  const image = <PedigreeImage
    family={family}
    disablePedigreeZoom={disablePedigreeZoom}
    size={compact ? 'small' : 'medium'}
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
        <PedigreeImage family={family} disablePedigreeZoom isEditable={isEditable} size="large" /><br />
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
