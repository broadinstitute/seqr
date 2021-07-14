import React from 'react'
import PropTypes from 'prop-types'
import $ from 'jquery'
import { Icon, Segment, Table } from 'semantic-ui-react'
import styled from 'styled-components'
import { svg2img } from 'pedigreejs/es/io'
import { build as buildPedigeeJs } from 'pedigreejs/es/pedigree'

import Modal from '../../modal/Modal'
import { NoBorderTable, FontAwesomeIconsContainer } from '../../StyledComponents'
import { EditPedigreeImageButton, DeletePedigreeImageButton } from './PedigreeImageButtons'

const PedigreeImg = styled.img.attrs({ alt: 'pedigree' })`
  max-height: ${props => props.maxHeight}px;
  max-width: 225px;
  vertical-align: top;
  cursor: ${props => (props.disablePedigreeZoom ? 'auto' : 'zoom-in')};
`

const PedigreeJsContainer = styled(FontAwesomeIconsContainer)`
  display: ${props => ((props.disablePedigreeZoom && props.isEditable) ? 'auto' : 'none')};
  cursor: ${props => (props.disablePedigreeZoom ? 'auto' : 'zoom-in')};

  i.fa {
    cursor: pointer;
  }
  
  .addchild, .addsibling, .addpartner, .addparents, .delete, .settings, .popup_selection {
    font-family: Icons !important;
    cursor: pointer;
    
    &.fa-circle, &.fa-square, &.fa-unspecified {
      font-family: outline-icons !important;
    }
  }
`

const MIN_INDIVS_PER_PEDIGREE = 2

class PedigreeImage extends React.PureComponent {

  static propTypes = {
    family: PropTypes.object,
    disablePedigreeZoom: PropTypes.bool,
    isEditable: PropTypes.bool,
  }

  constructor(props) {
    super(props)
    this.containerId = `pedigreeJS-${props.family.familyGuid}`
    this.state = { imgSrc: props.family.pedigreeImage }
  }

  setContainerElement = (element) => {
    this.container = element
  }

  render() {
    const { family, ...props } = this.props
    return this.state.imgSrc ? <PedigreeImg src={this.state.imgSrc} {...props} /> : (
      <PedigreeJsContainer {...props}>
        <div id={`${this.containerId}-buttons`} />
        <div ref={this.setContainerElement} id={this.containerId} />
      </PedigreeJsContainer>)
  }

  componentDidMount() {
    if (this.state.imgSrc) {
      return
    }

    const { disablePedigreeZoom, isEditable } = this.props
    const dataset = [ // TODO
      { name: 'm21', sex: 'M', top_level: true },
      { name: 'f21', sex: 'F', top_level: true },
      { name: 'ch1', sex: 'F', mother: 'f21', father: 'm21', affected: true },
    ]
    const opts = {
      dataset,
      targetDiv: this.containerId,
      btn_target: `${this.containerId}-buttons`,
      edit: true,
      background: '#fff',
      diseases: [{ type: 'affected', colour: '#111' }],
      labels: ['name'],
      zoomIn: 100,
      zoomOut: 100,
      font_size: '1.5em',
      symbol_size: 40,
      store_type: 'array', // TODO remove
    }
    buildPedigeeJs(opts)

    if (disablePedigreeZoom && isEditable) {
      // Because of how text content is set for these icons, there is no way to override the unicode value with css
      $('.fa-circle').text('\uf111 ')
      $('.fa-square').text('\uf0c8 ')
      $('.fa-unspecified').text('\uf0c8 ')
    } else {
      const svg = $(this.container.children[0])
      svg2img(svg, 'pedigree', { resolution: 10 }).done((args) => {
        this.setState({ imgSrc: args.img })
      })
    }
  }
}

const PedigreeImagePanel = React.memo(({ family, isEditable, compact, disablePedigreeZoom }) => {
  const image = <PedigreeImage
    family={family}
    disablePedigreeZoom={disablePedigreeZoom}
    maxHeight={compact ? '35' : '150'}
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
        <PedigreeImage family={family} disablePedigreeZoom isEditable={isEditable} maxHeight="250" /><br />
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
