import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Form, Accordion, Header, Segment, Grid } from 'semantic-ui-react'

import { VerticalSpacer } from 'shared/components/Spacers'
import { fieldLabel, configuredFields } from 'shared/components/form/ReduxFormWrapper'
import { Select, LabeledSlider } from 'shared/components/form/Inputs'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import FrequencyFilter from './filters/FrequencyFilter'
import {
  FREQUENCIES,
  CLINVAR_ANNOTATION_GROUPS,
  HGMD_ANNOTATION_GROUPS,
  VEP_ANNOTATION_GROUPS,
  QUALITY_FILTER_FIELDS,
  QUALITY_FILTER_OPTIONS,
} from '../constants'


const OPTIONS = [...CLINVAR_ANNOTATION_GROUPS, ...HGMD_ANNOTATION_GROUPS, ...VEP_ANNOTATION_GROUPS].reduce(
  (acc, { name, children }) =>
    [...acc, ...children.map(child => ({ category: name, value: child, text: snakecaseToTitlecase(child) }))],
  [],
)

const ToggleHeader = styled(Header).attrs({ size: 'huge', block: true })`
  .dropdown.icon {
    vertical-align: middle !important;
  }

  .content {
    display: inline-block !important;
    width: calc(100% - 2em);
  }
`

const ToggleHeaderFieldColumn = styled(Grid.Column)`
  font-size: 0.75em;
      
  .fields {
    margin: 0 !important;
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

const FormSelect = props =>
  <Form.Select {...props} onChange={(e, fieldProps) => fieldProps.onChange(fieldProps.value)} />

FormSelect.propTypes = {
  input: PropTypes.object,
}

const ToggleHeaderContent = ({ name, title, inputProps, inputSize }) =>
  <Header.Content>
    <Grid>
      <Grid.Row>
        <Grid.Column width={8} verticalAlign="middle">{title}</Grid.Column>
        {inputProps &&
          <ToggleHeaderFieldColumn width={inputSize || 3} floated="right" onClick={e => e.stopPropagation()}>
            {/* TODO remove custom format/ parse once using POST */}
            {configuredFields({ fields: [{ ...inputProps, name, format: val => inputProps.format(JSON.parse(val)), parse: val => JSON.stringify(inputProps.parse(val)) }] })}
          </ToggleHeaderFieldColumn>
        }
      </Grid.Row>
    </Grid>
  </Header.Content>

ToggleHeaderContent.propTypes = {
  title: PropTypes.string.isRequired,
  name: PropTypes.string,
  inputProps: PropTypes.object,
  inputSize: PropTypes.number,
}

const FilterFields = ({ value, onChange, fields, helpText, control }) =>
  <div>
    { helpText && <i>{helpText} <VerticalSpacer height={20} /></i>}
    <Form.Group widths="equal">
      {fields.map(({ field, label, labelHelp, ...fieldProps }) =>
        <Form.Field
          key={field}
          value={value[field]}
          onChange={val => onChange({ ...value, [field]: val })}
          label={fieldLabel(label, labelHelp)}
          control={control}
          {...fieldProps}
        />,
      )}
    </Form.Group>
  </div>

FilterFields.propTypes = {
  value: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  fields: PropTypes.array.isRequired,
  helpText: PropTypes.string,
  control: PropTypes.func,
}


const PANEL_DETAILS = [
  {
    name: 'annotations',
    headerProps: { title: 'Variant Annotations' },
    fieldProps: {
      component: FormSelect,
      label: 'Annotation',
      options: OPTIONS,
      multiple: true,
      format: val => val.split(','),
      parse: val => val.join(','),
    },
  },
  {
    name: 'freqs',
    headerProps: {
      title: 'Frequency',
      inputSize: 6,
      inputProps: {
        component: FrequencyFilter,
        format: values => Object.values(values).reduce((acc, value) => ({
          af: value.af === acc.af ? value.af : null,
          ac: value.ac === acc.ac ? value.ac : null,
          hh: value.hh === acc.hh ? value.hh : null,
        }), Object.values(values)[0]),
        parse: value => FREQUENCIES.reduce((acc, { field }) => ({ ...acc, [field]: value }), {}),
        homHemi: true,
        inlineSlider: true,
      },
    },
    fieldProps: {
      fields: FREQUENCIES,
      control: FrequencyFilter,
      helpText: 'Filter by allele frequency (popmax AF where available) or by allele count (AC). In applicable populations, also filter by homozygous/hemizygous count (H/H).',
    },
  },
  {
    name: 'qualityFilter',
    headerProps: {
      title: 'Call Quality',
      inputProps: { component: Select, format: JSON.stringify, parse: JSON.parse, options: QUALITY_FILTER_OPTIONS },
    },
    fieldProps: { fields: QUALITY_FILTER_FIELDS, control: LabeledSlider },
  },
]


const PANELS = PANEL_DETAILS.map(({ name, headerProps, fieldProps }, i) => ({
  key: name,
  title: {
    key: `${name}-title`,
    as: ToggleHeader,
    attached: i === 0 ? 'top' : true,
    content: <ToggleHeaderContent name={name} {...headerProps} />,
  },
  content: {
    key: name,
    as: Segment,
    attached: i === PANEL_DETAILS.length - 1 ? 'bottom' : true,
    padded: true,
    textAlign: 'center',
    content: configuredFields({ fields: [{
      name,
      component: FilterFields,
      format: val => JSON.parse(val), // TODO remove once using POST
      parse: val => JSON.stringify(val), // TODO remove once using POST
      ...fieldProps,
    }] }),
  },
}))

const VariantSearchForm = () => <Accordion fluid defaultActiveIndex={1} panels={PANELS} />

export default VariantSearchForm
