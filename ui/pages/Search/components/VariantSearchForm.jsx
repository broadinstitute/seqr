import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { FormSection } from 'redux-form'
import { Form, Accordion, Header, Segment, Grid, List } from 'semantic-ui-react'

import { VerticalSpacer } from 'shared/components/Spacers'
import ButtonLink from 'shared/components/buttons/ButtonLink'
import { configuredFields } from 'shared/components/form/ReduxFormWrapper'
import { Select, LabeledSlider, CheckboxGroup } from 'shared/components/form/Inputs'
import Modal from 'shared/components/modal/Modal'
import { LOCUS_LIST_ITEMS_FIELD, AFFECTED, UNAFFECTED } from 'shared/utils/constants'
import FrequencyFilter from './filters/FrequencyFilter'
import annotationsFilterLayout from './filters/AnnotationsFilterLayout'
import { LocusListSelector } from './filters/LocationFilter'
import CustomInheritanceFilter from './filters/CustomInheritanceFilter'
import {
  INHERITANCE_FILTER_OPTIONS,
  INHERITANCE_LOOKUP,
  INHERITANCE_MODE_LOOKUP,
  ALL_INHERITANCE_FILTER,
  NUM_ALT_OPTIONS,
  FREQUENCIES,
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
      
  .dropdown.icon {
    margin: -0.75em !important;
    transform: rotate(90deg) !important;
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

const JsonSelectProps = options => ({
  component: Select,
  format: JSON.stringify,
  parse: JSON.parse,
  options: options.map(({ value, ...option }) => ({ ...option, value: JSON.stringify(value) })),
})

const INHERITANCE_PANEL = {
  name: 'inheritance',
  headerProps: {
    title: 'Inheritance',
    inputProps: {
      component: Select,
      options: INHERITANCE_FILTER_OPTIONS,
      format: val => ((val || {}).filter ? INHERITANCE_MODE_LOOKUP[JSON.stringify(val.filter)] : ALL_INHERITANCE_FILTER),
      normalize: val => (val === ALL_INHERITANCE_FILTER ? null : { filter: INHERITANCE_LOOKUP[val].filter, mode: val }),
    },
  },
  fields: [
    { name: `filter.${AFFECTED}.genotype`, label: 'Affected Allele Counts' },
    { name: `filter.${UNAFFECTED}.genotype`, label: 'Unaffected Allele Counts' },
    {
      name: 'filter',
      label: 'Custom Allele Counts',
      width: 8,
      control: CustomInheritanceFilter,
      format: val => val || {},
    },
  ],
  fieldProps: { control: Select, options: NUM_ALT_OPTIONS, width: 4 },
  helpText: (
    <span>
      Filter by the mode of inheritance. Choose from the built-in search methods (described
      <Modal trigger={<ButtonLink> here</ButtonLink>} title="Inheritance Searching" modalName="inheritanceModes">
        <i>seqr</i> implements the following set of standard Mendelian inheritance methods to identify variants that
        segregate with a phenotype in a family
        {INHERITANCE_FILTER_OPTIONS.filter(({ value }) => value !== ALL_INHERITANCE_FILTER).map(({ text, value }) =>
          <Header key={value} content={text} subheader={INHERITANCE_LOOKUP[value].description} />,
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
      </Modal>) or specify custom alternate allele counts
    </span>
  ),
}

const ANNOTATION_PANEL = {
  name: 'annotations',
  headerProps: { title: 'Annotations', inputProps: JsonSelectProps(ANNOTATION_FILTER_OPTIONS) },
  fields: ANNOTATION_GROUPS,
  fieldProps: { control: CheckboxGroup, format: val => val || [] },
  fieldLayout: annotationsFilterLayout,
}

const FREQUENCY_PANEL = {
  name: 'freqs',
  headerProps: {
    title: 'Frequency',
    inputSize: 6,
    inputProps: {
      component: FrequencyFilter,
      format: values => (values ? Object.values(values).reduce((acc, value) => ({
        af: value.af === acc.af ? value.af : null,
        ac: value.ac === acc.ac ? value.ac : null,
        hh: value.hh === acc.hh ? value.hh : null,
      }), Object.values(values)[0]) : {}),
      parse: value => FREQUENCIES.reduce((acc, { name }) => ({ ...acc, [name]: value }), {}),
      homHemi: true,
      inlineSlider: true,
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
    name: `locus.${LOCUS_LIST_ITEMS_FIELD.name}`,
    inputSize: 5,
    inputProps: { component: LocusListSelector, format: val => val || {} },
  },
  fields: LOCATION_FIELDS,
  helpText: 'Filter by variant location. Entries can be either gene symbols (e.g. CFTR) or intervals in the form <chrom>:<start>-<end>. Entries can be separated by commas or whitespace.',
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
          {configuredFields({ fields: [{ ...inputProps, name }] })}
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
      {fieldLayout ? fieldLayout(fieldComponents) : <Form.Group widths="equal">{fieldComponents}</Form.Group>}
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

const PANEL_DETAILS = [INHERITANCE_PANEL, ANNOTATION_PANEL, FREQUENCY_PANEL, LOCATION_PANEL, QUALITY_PANEL]
const PANELS = PANEL_DETAILS.map(({ name, headerProps, ...panelContentProps }, i) => ({
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
}))


export default () => <Accordion fluid panels={PANELS} />
