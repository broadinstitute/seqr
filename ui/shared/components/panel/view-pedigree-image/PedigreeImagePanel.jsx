import React from 'react'
import PropTypes from 'prop-types'
import { Icon, Segment, Table } from 'semantic-ui-react'
import styled from 'styled-components'
import { build as buildPedigeeJs } from 'pedigreejs/es/pedigree'

import Modal from '../../modal/Modal'
import { NoBorderTable } from '../../StyledComponents'
import { EditPedigreeImageButton, DeletePedigreeImageButton } from './PedigreeImageButtons'

const UploadedPedigreeImage = styled.img.attrs({ alt: 'pedigree' })`
  max-height: ${props => props.height}px;
  max-width: 225px;
  vertical-align: top;
  cursor: ${props => (props.disablePedigreeZoom ? 'auto' : 'zoom-in')};
`

const MIN_INDIVS_PER_PEDIGREE = 2

class PedigreeJs extends React.PureComponent {

  static propTypes = {
    family: PropTypes.object,
  }

  constructor(props) {
    super(props)
    this.containerId = `pedigreeJS-${props.family.familyGuid}`
  }

  render() {
    return <div id={this.containerId} />
  }

  componentDidMount() {
    const dataset = [
      { name: 'm21', sex: 'M', top_level: true },
      { name: 'f21', sex: 'F', top_level: true },
      { name: 'ch1', sex: 'F', mother: 'f21', father: 'm21', breast_cancer: true, proband: true },
    ]
    const opts = {
      dataset,
      targetDiv: this.containerId,
      height: this.props.height,
      width: this.props.height * 1.5,
      // zoomOut: 3,
      symbol_size: 30,
      // 'btn_target': 'pedigree_history',
      // 'width': 450,
      // 'height': 320,
      // 'symbol_size': 35,
      // 'store_type': 'array',
      // 'diseases': [],
      // labels: ['age', 'yob'],
      // font_size: '.75em',
      // font_family: 'Helvetica',
      // font_weight: 700,
    }
    buildPedigeeJs(opts)
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
    height={compact ? 35 : 150}
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
        <PedigreeImage family={family} disablePedigreeZoom height={250} /><br />
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
