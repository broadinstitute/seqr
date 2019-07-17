import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { FormSection } from 'redux-form'
import { Form, Accordion, Header, Segment, Grid, List, Icon } from 'semantic-ui-react'

import { getUser } from 'redux/selectors'
import { VerticalSpacer } from 'shared/components/Spacers'
import { ButtonLink, InlineHeader } from 'shared/components/StyledComponents'
import { configuredField, configuredFields } from 'shared/components/form/ReduxFormWrapper'
import { Select, LabeledSlider, AlignedCheckboxGroup } from 'shared/components/form/Inputs'
import Modal from 'shared/components/modal/Modal'
import { SavedSearchDropdown } from './SavedSearch'
import FrequencyFilter from './filters/FrequencyFilter'
import annotationsFilterLayout from './filters/AnnotationsFilterLayout'
import LocusListSelector from './filters/LocusListSelector'
import CustomInheritanceFilter from './filters/CustomInheritanceFilter'
import ProjectFamiliesField from './filters/ProjectFamiliesField'
import {
  INHERITANCE_FILTER_OPTIONS,
  INHERITANCE_LOOKUP,
  INHERITANCE_MODE_LOOKUP,
  ALL_INHERITANCE_FILTER,
  NUM_ALT_OPTIONS,
  THIS_CALLSET_FREQUENCY,
  FREQUENCIES,
  PATHOGENICITY_FIELDS,
  PATHOGENICITY_FILTER_OPTIONS,
  STAFF_PATHOGENICITY_FIELDS,
  STAFF_PATHOGENICITY_FILTER_OPTIONS,
  ANNOTATION_GROUPS,
  ANNOTATION_FILTER_OPTIONS,
  QUALITY_FILTER_FIELDS,
  QUALITY_FILTER_OPTIONS,
  LOCATION_FIELDS,
} from '../constants'


const ToggleHeader = styled(Header).attrs({ size: 'huge', block: true })`
  .dropdown.icon {
    vertical-align: middle !important;
  }

  .grid {
    display: inline-block !important;
    width: calc(100% - 2em);
  }
`

const ToggleHeaderFieldColumn = styled(Grid.Column)`
  font-size: 0.75em;
      
  .fields {
    margin: 0 !important;
    
    &.inline .field:last-child {
      padding-right: 0 !important;
    }
  }
  
  .inline.field  {
    padding-right: 0 !important;
  }
      
  .dropdown {
    &.fluid {
      width: 100% !important;
    }
    
    .icon {
      margin: -0.75em !important;
      transform: rotate(90deg) !important;
    }
  }
      
  .rangeslider {
    margin: 1.2em;
    font-weight: 300;
    font-size: .9em;
    
    .rangeslider__labels {
      font-size: .5em;
    }
  }
`

const DetailLink = styled(ButtonLink)`
  &.ui.button.basic {
    margin-left: .2em;
    margin-right: 0;
    font-weight: initial;
    font-style: inherit;
  }
`

const ExpandCollapseCategoryContainer = styled.span`
  float: right;
  padding-top: 1em;
`

const JsonSelectProps = options => ({
  component: Select,
  format: JSON.stringify,
  parse: JSON.parse,
  options: options.map(({ value, ...option }) => ({ ...option, value: JSON.stringify(value) })),
})

const SAVED_SEARCH_FIELD = {
  name: 'search',
  component: SavedSearchDropdown,
  format: val => val || {},
}

const INHERITANCE_PANEL = {
  name: 'inheritance',
  headerProps: {
    title: 'Inheritance',
    inputProps: {
      component: Select,
      options: INHERITANCE_FILTER_OPTIONS,
      format: (val) => {
        if (!(val || {}).filter) {
          return ALL_INHERITANCE_FILTER
        }
        if (val.filter.genotype) {
          return null
        }
        const { affected, genotype, ...coreFilter } = val.filter
        return INHERITANCE_MODE_LOOKUP[JSON.stringify(coreFilter)]
      },
      normalize: (val, prevVal) => (val === ALL_INHERITANCE_FILTER ? null :
        { mode: val, filter: { affected: ((prevVal || {}).filter || {}).affected, ...INHERITANCE_LOOKUP[val].filter } }),
    },
  },
  fields: [
    {
      name: 'filter',
      width: 8,
      control: CustomInheritanceFilter,
      format: val => val || {},
    },
  ],
  fieldProps: { control: Select, options: NUM_ALT_OPTIONS },
  helpText: (
    <span>
      Filter by the mode of inheritance. Choose from the built-in search methods (described
      <Modal trigger={<DetailLink>here</DetailLink>} title="Inheritance Searching" modalName="inheritanceModes">
        <i>seqr</i> implements the following set of standard Mendelian inheritance methods to identify variants that
        segregate with a phenotype in a family
        {INHERITANCE_FILTER_OPTIONS.filter(({ value }) => value !== ALL_INHERITANCE_FILTER).map(({ value, text, detail }) =>
          <Header key={value} content={text} subheader={detail} />,
        )}

        <Header size="small" content="Notes on inheritance searching:" />
        <List bulleted>
          <List.Item>
            These methods rely on the affected status of individuals. Individuals with an Unknown phenotype will
            not be taken into consideration for genotype filters
          </List.Item>
          <List.Item>All methods assume complete penetrance</List.Item>
          <List.Item>seqr assumes unphased genotypes</List.Item>
        </List>
      </Modal>) or specify custom alternate allele counts. You can also specify the affected status for an individual
      that differs from the status in the pedigree.
    </span>
  ),
}


const pathogenicityPanel = isStaff => ({
  name: 'pathogenicity',
  headerProps: { title: 'Pathogenicity', inputProps: JsonSelectProps(isStaff ? STAFF_PATHOGENICITY_FILTER_OPTIONS : PATHOGENICITY_FILTER_OPTIONS) },
  fields: isStaff ? STAFF_PATHOGENICITY_FIELDS : PATHOGENICITY_FIELDS,
  fieldProps: { control: AlignedCheckboxGroup, format: val => val || [] },
  helpText: 'Filter by reported pathogenicity. Note this filter will override any annotations filter (i.e variants will be returned if they have either the specified pathogenicity OR transcript consequence)',
})

const STAFF_PATHOGENICITY_PANEL = pathogenicityPanel(true)
const PATHOGENICITY_PANEL = pathogenicityPanel(false)

const ANNOTATION_PANEL = {
  name: 'annotations',
  headerProps: { title: 'Annotations', inputProps: JsonSelectProps(ANNOTATION_FILTER_OPTIONS) },
  fields: ANNOTATION_GROUPS,
  fieldProps: { control: AlignedCheckboxGroup, format: val => val || [] },
  fieldLayout: annotationsFilterLayout,
}

const FREQUENCY_PANEL = {
  name: 'freqs',
  headerProps: {
    title: 'Frequency',
    inputSize: 6,
    inputProps: {
      component: FrequencyFilter,
      format: (values) => {
        if (!values) {
          return {}
        }
        const { callset, ...freqValues } = values
        return Object.values(freqValues).reduce((acc, value) => ({
          af: value.af === acc.af ? value.af : null,
          ac: value.ac === acc.ac ? value.ac : null,
          hh: value.hh === acc.hh ? value.hh : null,
        }), Object.values(freqValues)[0])
      },
      parse: value => FREQUENCIES.reduce((acc, { name }) => (name === THIS_CALLSET_FREQUENCY ? acc : { ...acc, [name]: value }), {}),
      homHemi: true,
      inlineAF: true,
    },
  },
  fields: FREQUENCIES,
  fieldProps: { control: FrequencyFilter, format: val => val || {} },
  helpText: 'Filter by allele frequency (popmax AF where available) or by allele count (AC). In applicable populations, also filter by homozygous/hemizygous count (H/H).',
}

const LOCATION_PANEL = {
  name: 'locus',
  headerProps: {
    title: 'Location',
    name: 'locus',
    inputSize: 5,
    inputProps: { component: LocusListSelector, format: val => val || {} },
  },
  fields: LOCATION_FIELDS,
  helpText: 'Filter by variant location. Entries can be either gene symbols (e.g. CFTR) or intervals in the form <chrom>:<start>-<end> (e.g. 4:6935002-87141054). Variant entries can be either rsIDs (e.g. rs61753695) or variants in the form <chrom>-<pos>-<ref>-<alt> (e.g. 4-88047328-C-T). Entries can be separated by commas or whitespace.',
}

const QUALITY_PANEL = {
  name: 'qualityFilter',
  headerProps: { title: 'Call Quality', inputProps: JsonSelectProps(QUALITY_FILTER_OPTIONS) },
  fields: QUALITY_FILTER_FIELDS,
  fieldProps: { control: LabeledSlider, format: val => val || null },
}


const HeaderContent = ({ name, title, inputSize, inputProps }) =>
  <Grid>
    <Grid.Row>
      <Grid.Column width={9} verticalAlign="middle">{title}</Grid.Column>
      {inputProps &&
        <ToggleHeaderFieldColumn width={inputSize || 3} floated="right" textAlign="right" onClick={e => e.stopPropagation()}>
          {configuredField({ ...inputProps, name })}
        </ToggleHeaderFieldColumn>
      }
    </Grid.Row>
  </Grid>

HeaderContent.propTypes = {
  title: PropTypes.string.isRequired,
  name: PropTypes.string,
  inputSize: PropTypes.number,
  inputProps: PropTypes.object,
}

const PanelContent = ({ name, fields, fieldProps, helpText, fieldLayout }) => {
  const fieldComponents = configuredFields({ fields: fields.map(field => ({ ...(fieldProps || {}), ...field })) })
  return (
    <FormSection name={name}>
      {helpText && <i>{helpText} <VerticalSpacer height={20} /></i>}
      <Form.Group widths="equal">
        <Form.Field width={2} />
        {fieldLayout ? fieldLayout(fieldComponents) : fieldComponents}
        <Form.Field width={2} />
      </Form.Group>
    </FormSection>
  )
}

PanelContent.propTypes = {
  fields: PropTypes.array.isRequired,
  name: PropTypes.string.isRequired,
  fieldProps: PropTypes.object,
  helpText: PropTypes.node,
  fieldLayout: PropTypes.func,
}

const PANEL_DETAILS = [
  INHERITANCE_PANEL, PATHOGENICITY_PANEL, ANNOTATION_PANEL, FREQUENCY_PANEL, LOCATION_PANEL, QUALITY_PANEL,
]
const STAFF_PANEL_DETAILS = [
  INHERITANCE_PANEL, STAFF_PATHOGENICITY_PANEL, ANNOTATION_PANEL, FREQUENCY_PANEL, LOCATION_PANEL, QUALITY_PANEL,
]

const panelDetails = ({ name, headerProps, ...panelContentProps }, i) => ({
  key: name,
  title: {
    key: `${name}-title`,
    as: ToggleHeader,
    attached: i === 0 ? 'top' : true,
    content: <HeaderContent name={name} {...headerProps} />,
  },
  content: {
    key: name,
    as: Segment,
    attached: i === PANEL_DETAILS.length - 1 ? 'bottom' : true,
    padded: true,
    textAlign: 'center',
    content: <PanelContent name={name} {...panelContentProps} />,
  },
})

const PANELS = PANEL_DETAILS.map(panelDetails)
const STAFF_PANELS = STAFF_PANEL_DETAILS.map(panelDetails)

class VariantSearchFormContent extends React.Component {
  state = { activeIndex: [] }

  expandAll = (e) => {
    e.preventDefault()
    this.setState({ activeIndex: [...PANELS.keys()] })
  }

  collapseAll = (e) => {
    e.preventDefault()
    this.setState({ activeIndex: [] })
  }

  handleTitleClick = (e, { index }) => {
    const { activeIndex } = this.state
    const newIndex = activeIndex.indexOf(index) === -1 ? [...activeIndex, index] : activeIndex.filter(item => item !== index)

    this.setState({ activeIndex: newIndex })
  }

  render() {
    return (
      <div>
        <ProjectFamiliesField />
        <VerticalSpacer height={10} />
        <InlineHeader content="Saved Search:" />
        {configuredField(SAVED_SEARCH_FIELD)}
        <ExpandCollapseCategoryContainer>
          <ButtonLink onClick={this.expandAll}>Expand All &nbsp;<Icon name="plus" /></ButtonLink>
          <b>| &nbsp;&nbsp;</b>
          <ButtonLink onClick={this.collapseAll}>Collapse All &nbsp;<Icon name="minus" /></ButtonLink>
        </ExpandCollapseCategoryContainer>
        <VerticalSpacer height={10} />
        <FormSection name="search">
          <Accordion fluid panels={this.props.user.isStaff ? STAFF_PANELS : PANELS} exclusive={false} activeIndex={this.state.activeIndex} onTitleClick={this.handleTitleClick} />
        </FormSection>
      </div>
    )
  }

  shouldComponentUpdate(nextProps, nextState) {
    // Form content does not use passed props, so should never re-render on prop update
    return nextState.activeIndex !== this.state.activeIndex
  }
}

VariantSearchFormContent.propTypes = {
  user: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(VariantSearchFormContent)
