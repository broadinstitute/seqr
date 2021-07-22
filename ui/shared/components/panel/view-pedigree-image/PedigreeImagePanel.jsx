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

import { getIndividualsByFamily } from 'redux/selectors'
import { openModal } from 'redux/utils/modalReducer'
import { INDIVIDUAL_FIELD_CONFIGS, INDIVIDUAL_FIELD_SEX, AFFECTED } from 'shared/utils/constants'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import ReduxFormWrapper from '../../form/ReduxFormWrapper'
import { BooleanCheckbox, InlineToggle, RadioGroup, YearSelector } from '../../form/Inputs'
import Modal from '../../modal/Modal'
import { NoBorderTable, FontAwesomeIconsContainer, ButtonLink } from '../../StyledComponents'
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

const EDIT_INDIVIDUAL_MODAL_ID = 'editPedIndividual'
const EDIT_INDIVIDUAL_FIELDS = [
  { name: 'display_name', label: 'Individual ID' },
  { name: 'affected', label: 'Affected?', component: InlineToggle, fullHeight: true, asFormInput: true },
  { name: INDIVIDUAL_FIELD_SEX, label: 'Sex', ...INDIVIDUAL_FIELD_CONFIGS[INDIVIDUAL_FIELD_SEX].formFieldProps },
  { name: 'yob', label: 'Birth Year', component: YearSelector, width: 6 },
  {
    name: 'status',
    label: 'Living?',
    component: RadioGroup,
    options: [{ value: 0, text: 'Alive' }, { value: 1, text: 'Deceased' }],
  },
  ...['adopted_in', 'adopted_out', 'miscarriage', 'termination'].map(name => (
    { name, label: snakecaseToTitlecase(name), component: BooleanCheckbox, inline: true }
  )),
]

const INDIVIDUAL_FIELD_MAP = {
  name: 'individualGuid',
  display_name: 'displayName',
  sex: 'sex',
  affected: 'affected',
  yob: 'birthYear',
  mother: 'maternalGuid',
  father: 'paternalGuid',
  status: 'deathYear',
}

class BasePedigreeImage extends React.PureComponent {

  static propTypes = {
    family: PropTypes.object,
    disablePedigreeZoom: PropTypes.bool,
    isEditable: PropTypes.bool,
    individuals: PropTypes.array,
    openIndividualModal: PropTypes.func,
  }

  constructor(props) {
    super(props)
    this.containerId = `pedigreeJS-${props.family.familyGuid}`
    this.state = {}
  }

  setContainerElement = (element) => {
    this.container = element
  }

  render() {
    const { family, ...props } = this.props
    const { editIndividual = {} } = this.state
    const pedImgSrc = this.getImageSrc()
    // TODO add save button for update pedigree
    return pedImgSrc ? <PedigreeImg src={pedImgSrc} {...props} /> : (
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
    if (!this.getImageSrc()) {
      this.setImage()
    }
  }

  componentDidUpdate(prevProps) {
    if (!this.props.family.pedigreeImage) {
      if (prevProps.family.pedigreeImage) {
        this.setImage()
      } else if (prevProps.individuals !== this.props.individuals) {
        this.setImage()
      }
    }
  }

  setImage() {
    const { disablePedigreeZoom, isEditable } = this.props
    const opts = {
      dataset: this.getFamilyDataset(),
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

  getImageSrc = () => this.props.family.pedigreeImage || this.state.imgSrc

  getFamilyDataset = () => {
    const { family, individuals } = this.props
    const dataset = family.pedigreeDataset || individuals.map(
      individual => Object.entries(INDIVIDUAL_FIELD_MAP).reduce((acc, [key, mappedKey]) => {
        let val = individual[mappedKey]
        if (key === 'affected') {
          val = val === AFFECTED
        } else if (key === 'status') {
          val = (!!val || val === 0) ? 1 : 0
        } else if (!val && (key === 'mother' || key === 'father')) {
          return acc
        }

        return { ...acc, [key]: val }
      }, {}),
    ).map(row => ({ ...row, top_level: !row.mother && !row.father }))

    return this.yobToAge(dataset)
  }

  yobToAge = dataset => dataset.map(o => ({ ...o, age: o.yob && new Date().getFullYear() - o.yob }))

  editIndividual = (opts, { data }) => {
    this.setState({
      editIndividual: {
        data,
        save: (newData) => {
          Object.assign(data, newData)
          opts.dataset = copyPedigreeDataset(this.yobToAge(opts.dataset))
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

const mapStateToProps = (state, ownProps) => ({
  individuals: getIndividualsByFamily(state)[ownProps.family.familyGuid],
})

const mapDispatchToProps = dispatch => ({
  openIndividualModal: () => {
    dispatch(openModal(EDIT_INDIVIDUAL_MODAL_ID))
  },
})

const PedigreeImage = connect(mapStateToProps, mapDispatchToProps)(BasePedigreeImage)


const PedigreeImagePanel = React.memo(({ family, isEditable, compact, disablePedigreeZoom }) => {
  const hasPedImage = family.pedigreeImage || family.pedigreeDataset || family.individualGuids.length > 1
  if (!hasPedImage && (!isEditable || compact)) {
    return null
  }

  const image = hasPedImage && <PedigreeImage
    family={family}
    disablePedigreeZoom={disablePedigreeZoom}
    maxHeight={compact ? '35' : '150'}
  />
  if (disablePedigreeZoom) {
    return image
  }

  const modalId = `Pedigree-${family.familyGuid}`
  return (
    <Modal
      modalName={modalId}
      title={`Family ${family.displayName}`}
      trigger={
        image ? <span>{compact && `(${family.individualGuids.length}) `} {image}</span>
          : <ButtonLink content="Edit Pedigree Image" icon="edit" />
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
