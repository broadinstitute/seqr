import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { ErrorBoundary } from 'react-error-boundary'
import $ from 'jquery'
import 'jquery-ui/ui/widgets/dialog'
import 'jquery-ui/themes/base/all.css'
import { Icon, Segment, Table } from 'semantic-ui-react'
import styled from 'styled-components'

import { svg2img } from 'pedigreejs/es/io'
import { current as currentDataset } from 'pedigreejs/es/pedcache'
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
import { EditPedigreeImageButton, DeletePedigreeImageButton, SavePedigreeDatasetButton } from './PedigreeImageButtons'

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

const PEDIGREE_JS_OPTS = {
  background: '#fff',
  diseases: [],
  labels: ['age'],
  zoomIn: 3,
  zoomOut: 3,
  zoomSrc: ['button'],
  symbol_size: 40,
}

class BasePedigreeImage extends React.PureComponent {

  static propTypes = {
    family: PropTypes.object,
    disablePedigreeZoom: PropTypes.bool,
    isEditable: PropTypes.bool,
    individuals: PropTypes.array,
    openIndividualModal: PropTypes.func,
    modalId: PropTypes.string,
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
    const { family, modalId, ...props } = this.props
    const { editIndividual = {} } = this.state
    const pedImgSrc = this.props.family.pedigreeImage || this.state.imgSrc
    return pedImgSrc ? <PedigreeImg src={pedImgSrc} {...props} /> : (
      <PedigreeJsContainer {...props}>
        <NoBorderTable basic="very" compact="very">
          <Table.Body>
            <Table.Row>
              <Table.Cell>
                <div id={`${this.containerId}-buttons`} />
              </Table.Cell>
              <Table.Cell collapsing>
                <SavePedigreeDatasetButton
                  modalId={modalId}
                  familyGuid={family.familyGuid}
                  getPedigreeDataset={this.getPedigreeDataset}
                />
              </Table.Cell>
            </Table.Row>
          </Table.Body>
        </NoBorderTable>
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
    if (!this.props.family.pedigreeImage) {
      this.drawPedigree()
    }
  }

  componentDidUpdate(prevProps, prevState) {
    if (!this.props.family.pedigreeImage) { // If has an uploaded pedigree image, that is displayed so no need to draw
      if (prevProps.family.pedigreeImage || // If uploaded pedigree image was deleted, draw
        (prevProps.family.pedigreeDataset !== this.props.family.pedigreeDataset) || // If saved dataset was updated, redraw
        (prevProps.individuals !== this.props.individuals && !this.props.family.pedigreeDataset) || // If individual data changed, redraw
        (prevState.imgSrc && !this.state.imgSrc)) // If computed image src was cleared, redraw
      {
        if (this.state.imgSrc) {
          this.unsetPedigreeImage() // Cannot redraw pedigree if not rendering the svg container, so unset image first
        } else {
          const pedigreeOpts = this.redrawPedigree(this.state.pedigreeOpts, this.getFamilyDataset())
          if (!this.isEditablePedigree()) {
            this.setPedigreeImage(pedigreeOpts)
          }
        }
      }
    }
  }

  drawPedigree() {
    const dataset = this.getFamilyDataset()
    const opts = {
      dataset: this.getFamilyDataset(),
      targetDiv: this.containerId,
      btn_target: `${this.containerId}-buttons`,
      edit: this.editIndividual,
      font_size: dataset.length < 6 ? '1.5em' : '.7em',
      ...PEDIGREE_JS_OPTS,
    }
    const pedigreeOpts = buildPedigeeJs(opts)

    if (this.isEditablePedigree()) {
      // The refresh behavior is confusing - rather than resetting the pedigree to the initial state,
      // it resets it to a generic trio pedigree with arbitrary labels. This will never be useful, so remove the button
      $('.fa-refresh').remove()
      this.setState({ pedigreeOpts })
    } else {
      // For un-editable pedigrees, display as an img
      this.setPedigreeImage(pedigreeOpts)
    }
  }

  redrawPedigree = (opts, dataset) => {
    opts.dataset = copyPedigreeDataset(this.yobToAge(dataset || opts.dataset))
    try {
      validatePedigree(opts)
    } catch (err) {
      pedigreeMessages('Error', err.message)
      throw err
    }
    rebuildPedigeeJs(opts)
    return opts
  }

  setPedigreeImage = (pedigreeOpts) => {
    const svg = $(this.container.children[0])
    svg2img(svg, 'pedigree', { resolution: 10 }).done(({ img }) => {
      this.setState({ pedigreeOpts, imgSrc: img })
    })
  }

  unsetPedigreeImage = () => {
    this.setState({ imgSrc: null })
  }

  isEditablePedigree = () => this.props.disablePedigreeZoom && this.props.isEditable

  getFamilyDataset = () => {
    const { family, individuals } = this.props
    const dataset = family.pedigreeDataset || (individuals || []).map(
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
    ).map(row => (row.mother || row.father ? row : { ...row, top_level: true }))

    // pedigree js does not support having only one parent for an individual
    const newParents = {}
    dataset.filter(
      ({ mother, father }) => (mother && !father) || ((!mother && father)),
    ).forEach((indiv) => {
      const placeholderId = `${indiv.mother || indiv.father}-spouse-placeholder`
      if (!newParents[placeholderId]) {
        newParents[placeholderId] = {
          name: placeholderId,
          sex: indiv.mother ? 'M' : 'F',
          top_level: true,
        }
      }
      if (indiv.mother) {
        indiv.father = placeholderId
      } else {
        indiv.mother = placeholderId
      }
    })

    return this.yobToAge([...dataset, ...Object.values(newParents)])
  }

  yobToAge = dataset => dataset.map(o => ({ ...o, age: o.yob && new Date().getFullYear() - o.yob }))

  editIndividual = (opts, { data }) => {
    this.setState({
      editIndividual: {
        data,
        save: (newData) => {
          Object.assign(data, newData)
          this.redrawPedigree(opts)
        },
      } })
    this.props.openIndividualModal()
  }

  getPedigreeDataset = () => {
    return currentDataset(this.state.pedigreeOpts)
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

// Do not crash the entire page if pedigree js is breaking
const PedigreeError = () => <Icon name="picture" />
const SafePedigreeImage = props =>
  <ErrorBoundary FallbackComponent={PedigreeError}><PedigreeImage {...props} /></ErrorBoundary>

const PedigreeImagePanel = React.memo(({ family, isEditable, compact, disablePedigreeZoom }) => {
  const hasPedImage = family.pedigreeImage || family.pedigreeDataset || family.individualGuids.length > 1
  if (!hasPedImage && (!isEditable || compact)) {
    return null
  }

  const image = hasPedImage && <SafePedigreeImage
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
        <SafePedigreeImage family={family} disablePedigreeZoom isEditable={isEditable} modalId={modalId} maxHeight="250" /><br />
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
