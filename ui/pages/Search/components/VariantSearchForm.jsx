import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { FormSection } from 'redux-form'
import { Form, Accordion, Header, Segment, Grid } from 'semantic-ui-react'

import { VerticalSpacer } from 'shared/components/Spacers'
import { configuredFields } from 'shared/components/form/ReduxFormWrapper'
import { Select, LabeledSlider, CheckboxGroup } from 'shared/components/form/Inputs'
import FrequencyFilter from './filters/FrequencyFilter'
import {
  FREQUENCIES,
  ANNOTATION_GROUPS,
  QUALITY_FILTER_FIELDS,
  QUALITY_FILTER_OPTIONS,
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

const PANEL_DETAILS = [
  {
    name: 'annotations',
    title: 'Annotations',
    fields: ANNOTATION_GROUPS,
    fieldProps: {
      component: CheckboxGroup,
      format: val => val || [],
    },
  },
  {
    name: 'freqs',
    title: 'Frequency',
    headerInputSize: 6,
    headerInputProps: {
      component: FrequencyFilter,
      format: values => Object.values(values).reduce((acc, value) => ({
        af: value.af === acc.af ? value.af : null,
        ac: value.ac === acc.ac ? value.ac : null,
        hh: value.hh === acc.hh ? value.hh : null,
      }), Object.values(values)[0]),
      parse: value => FREQUENCIES.reduce((acc, { name }) => ({ ...acc, [name]: value }), {}),
      homHemi: true,
      inlineSlider: true,
    },
    fields: FREQUENCIES,
    fieldProps: { control: FrequencyFilter },
    helpText: 'Filter by allele frequency (popmax AF where available) or by allele count (AC). In applicable populations, also filter by homozygous/hemizygous count (H/H).',
  },
  {
    name: 'qualityFilter',
    title: 'Call Quality',
    headerInputProps: { component: Select, format: JSON.stringify, parse: JSON.parse, options: QUALITY_FILTER_OPTIONS },
    fields: QUALITY_FILTER_FIELDS,
    fieldProps: { control: LabeledSlider },
  },
]


const PANELS = PANEL_DETAILS.map(({ name, fields, fieldProps, helpText, title, headerInputProps, headerInputSize }, i) => ({
  key: name,
  title: {
    key: `${name}-title`,
    as: ToggleHeader,
    attached: i === 0 ? 'top' : true,
    content: (
      <Grid>
        <Grid.Row>
          <Grid.Column width={8} verticalAlign="middle">{title}</Grid.Column>
          {headerInputProps &&
            <ToggleHeaderFieldColumn width={headerInputSize || 3} floated="right" onClick={e => e.stopPropagation()}>
              {configuredFields({ fields: [{ ...headerInputProps, name }] })}
            </ToggleHeaderFieldColumn>
          }
        </Grid.Row>
      </Grid>
    ),
  },
  content: {
    key: name,
    as: Segment,
    attached: i === PANEL_DETAILS.length - 1 ? 'bottom' : true,
    padded: true,
    textAlign: 'center',
    content: (
      <FormSection name={name}>
        { helpText && <i>{helpText} <VerticalSpacer height={20} /></i>}
        <Form.Group widths="equal">
          {configuredFields({ fields: fields.map(field => ({ ...(fieldProps || {}), ...field })) })}
        </Form.Group>
      </FormSection>
    ),
  },
}))

const VariantSearchForm = () => <Accordion fluid defaultActiveIndex={0} panels={PANELS} />

export default VariantSearchForm
