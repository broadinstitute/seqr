import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import $ from 'jquery'
import 'jquery-ui/ui/widgets/dialog'
import 'jquery-ui/themes/base/all.css'
import { Icon, Segment, Table } from 'semantic-ui-react'
import styled from 'styled-components'

import { svg2img } from 'pedigreejs/es/io'
import {
  build as buildPedigeeJs, rebuild as rebuildPedigeeJs, validate_pedigree as validatePedigree,
} from 'pedigreejs/es/pedigree'
import { copy_dataset as copyPedigreeDataset, messages as pedigreeMessages } from 'pedigreejs/es/pedigree_utils'

import { openModal } from 'redux/utils/modalReducer'
import { INDIVIDUAL_FIELD_CONFIGS, INDIVIDUAL_FIELD_SEX } from 'shared/utils/constants'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import ReduxFormWrapper from '../../form/ReduxFormWrapper'
import { BooleanCheckbox, InlineToggle, RadioGroup, IntegerInput } from '../../form/Inputs'
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
  
  @font-face {
    font-family: 'ped-icon-overrides';
    src: url("/static/fonts/icon-overrides.eot");
    src: url("/static/fonts/icon-overrides.eot?#iefix") format('embedded-opentype'), url("/static/fonts/icon-overrides.woff") format('woff'), url("/static/fonts/icon-overrides.ttf") format('truetype'), url("/static/fonts/icon-overrides.svg#icons") format('svg');
  }
  
  .addchild, .addsibling, .addpartner, .addparents, .delete, .settings, .popup_selection {
    font-family: Icons !important;
    cursor: pointer;
    
    &.fa-circle, &.fa-square, &.fa-unspecified {
      font-family: ped-icon-overrides !important;
    }
  }
`

const MIN_INDIVS_PER_PEDIGREE = 2

const EDIT_INDIVIDUAL_MODAL_ID = 'editPedIndividual'
const EDIT_INDIVIDUAL_FIELDS = [
  { name: 'display_name', label: 'Individual ID' },
  { name: 'affected', label: 'Affected?', component: InlineToggle, fullHeight: true, asFormInput: true },
  { name: INDIVIDUAL_FIELD_SEX, label: 'Sex', ...INDIVIDUAL_FIELD_CONFIGS[INDIVIDUAL_FIELD_SEX].formFieldProps },
  {
    name: 'status',
    label: 'Living?',
    component: RadioGroup,
    options: [{ value: 0, text: 'Alive' }, { value: 1, text: 'Deceased' }],
  },
  { name: 'age', label: 'Age', component: IntegerInput, width: 4 }, //TODO yob and normalize to age?
  ...['adopted_in', 'adopted_out', 'miscarriage', 'termination'].map(name => (
    { name, label: snakecaseToTitlecase(name), component: BooleanCheckbox, inline: true }
  )),
]//

class BasePedigreeImage extends React.PureComponent {

  static propTypes = {
    family: PropTypes.object,
    disablePedigreeZoom: PropTypes.bool,
    isEditable: PropTypes.bool,
    openIndividualModal: PropTypes.func,
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
    const { imgSrc, editIndividual = {} } = this.state
    return imgSrc ? <PedigreeImg src={imgSrc} {...props} /> : (
      <PedigreeJsContainer {...props}>
        <div id={`${this.containerId}-buttons`} />
        <div ref={this.setContainerElement} id={this.containerId} />
        <Modal title={(editIndividual.data || {}).display_name} modalName={EDIT_INDIVIDUAL_MODAL_ID}>
          <ReduxFormWrapper
            onSubmit={editIndividual.save}
            form={EDIT_INDIVIDUAL_MODAL_ID}
            initialValues={editIndividual.data}
            fields={EDIT_INDIVIDUAL_FIELDS}
            submitButtonText="Update"
            confirmCloseIfNotSaved
          />
        </Modal>
      </PedigreeJsContainer>)
  }

  componentDidMount() {
    if (this.state.imgSrc) {
      return
    }

    const { disablePedigreeZoom, isEditable } = this.props
    const dataset = [ // TODO from family, map yob to age
      { name: 'm21', display_name: 'dad', sex: 'M', top_level: true, yob: 1983 },
      { name: 'f21', display_name: 'mom', sex: 'F', top_level: true, age: 30 },
      { name: 'ch1', sex: 'F', display_name: 'proband', mother: 'f21', father: 'm21', affected: true, age: 2 },
    ]
    const opts = {
      dataset,
      targetDiv: this.containerId,
      btn_target: `${this.containerId}-buttons`,
      edit: this.editIndividual,
      background: '#fff',
      diseases: [],
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
    } else {
      // For un-editable pedigrees, display as an img
      const svg = $(this.container.children[0])
      svg2img(svg, 'pedigree', { resolution: 10 }).done(({ img }) => {
        this.setState({ imgSrc: img })
      })
    }
  }

  editIndividual = (opts, { data }) => {
    this.setState({
      editIndividual: {
        data,
        save: (newData) => {
          Object.assign(data, newData)
          opts.dataset = copyPedigreeDataset(opts.dataset)
          try {
            validatePedigree(opts)
          } catch (err) {
            pedigreeMessages('Error', err.message)
            throw err
          }
          rebuildPedigeeJs(opts)
        },
      } })
    this.props.openIndividualModal()
  }
}

const mapDispatchToProps = dispatch => ({
  openIndividualModal: () => {
    dispatch(openModal(EDIT_INDIVIDUAL_MODAL_ID))
  },
})

const PedigreeImage = connect(null, mapDispatchToProps)(BasePedigreeImage)

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
