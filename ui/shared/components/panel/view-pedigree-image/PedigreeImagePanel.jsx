import React from 'react'
import PropTypes from 'prop-types'
import $ from 'jquery'
import 'jquery-ui/ui/widgets/dialog'
import 'jquery-ui/themes/base/all.css'
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
        <div id="node_properties" />
      </PedigreeJsContainer>)
  }

  componentDidMount() {
    if (this.state.imgSrc) {
      return
    }

    const { disablePedigreeZoom, isEditable } = this.props
    const dataset = [ // TODO from family, map yob to age
      { name: 'm21', display_name: 'mom', sex: 'M', top_level: true, yob: 1983 },
      { name: 'f21', display_name: 'dad', sex: 'F', top_level: true, age: 30 },
      { name: 'ch1', sex: 'F', display_name: 'proband', mother: 'f21', father: 'm21', affected: true, age: 2 },
    ]
    const opts = {
      dataset,
      targetDiv: this.containerId,
      btn_target: `${this.containerId}-buttons`,
      edit: true, // TODO configure editable fields
      background: '#fff',
      diseases: [{ type: 'affected', colour: '#11111191' }],
      labels: ['age'],
      zoomIn: 3,
      zoomOut: 3,
      zoomSrc: ['button'],
      font_size: '1.5em',
      symbol_size: 40,
      store_type: 'array', // TODO remove
    }
    buildPedigeeJs(opts)

    if (disablePedigreeZoom && isEditable) {
      // The refresh behavior is confusing - rather than resetting the pedigree to the initial state,
      // it resets it to a generic trio pedigree with arbitrary labels. This will never be useful, so remove the button
      $('.fa-refresh').remove()
      // Because of how text content is set for these icons, there is no way to override the unicode value with css TODO does not work after edit
      // $('.fa-circle').text('\uf111 ')
      // $('.fa-square').text('\uf0c8 ')
      // $('.fa-unspecified').text('\uf0c8 ')
    } else {
      // For un-editable pedigrees, display as an img
      const svg = $(this.container.children[0])
      svg2img(svg, 'pedigree', { resolution: 10 }).done(({ img }) => {
        this.setState({ imgSrc: img })
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
