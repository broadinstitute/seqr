import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { FormSection } from 'redux-form'
import { Form, Accordion, Header, Segment, Grid, Icon } from 'semantic-ui-react'

import { VerticalSpacer } from 'shared/components/Spacers'
import { ButtonLink } from 'shared/components/StyledComponents'
import { Select, LabeledSlider, AlignedCheckboxGroup } from 'shared/components/form/Inputs'
import { configuredField, configuredFields } from 'shared/components/form/ReduxFormWrapper'
import { VEP_GROUP_OTHER, VEP_GROUP_SV, VEP_GROUP_SV_CONSEQUENCES } from 'shared/utils/constants'

import { FrequencyFilter, HeaderFrequencyFilter } from './FrequencyFilter'
import {
  FREQUENCIES,
  PATHOGENICITY_FIELDS,
  PATHOGENICITY_FILTER_OPTIONS,
  HGMD_PATHOGENICITY_FIELDS,
  HGMD_PATHOGENICITY_FILTER_OPTIONS,
  ANY_PATHOGENICITY_FILTER,
  ANNOTATION_GROUPS,
  ANNOTATION_FILTER_OPTIONS,
  ALL_ANNOTATION_FILTER_DETAILS,
  QUALITY_FILTER_FIELDS,
  QUALITY_FILTER_OPTIONS,
  ALL_QUALITY_FILTER,
  LOCATION_FIELDS,
  CODING_IMPACT_GROUPS,
  HIGH_IMPACT_GROUPS_NO_SV,
  MODERATE_IMPACT_GROUPS,
} from './constants'

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

const ExpandCollapseCategoryContainer = styled.span`
  float: right;
  position: relative;
  top: -2em;
`

const JsonSelectPropsWithAll = (options, all) => ({
  component: Select,
  format: val => JSON.stringify(val) || JSON.stringify(all.value),
  parse: val => JSON.parse(val),
  options: options.map(({ value, ...option }) => ({ ...option, value: JSON.stringify(value) })),
})

const pathogenicityPanel = hasHgmdPermission => ({
  name: 'pathogenicity',
  headerProps: { title: 'Pathogenicity', inputProps: JsonSelectPropsWithAll(hasHgmdPermission ? HGMD_PATHOGENICITY_FILTER_OPTIONS : PATHOGENICITY_FILTER_OPTIONS, ANY_PATHOGENICITY_FILTER) },
  fields: hasHgmdPermission ? HGMD_PATHOGENICITY_FIELDS : PATHOGENICITY_FIELDS,
  fieldProps: { control: AlignedCheckboxGroup, format: val => val || [] },
  helpText: 'Filter by reported pathogenicity. Note this filter will override any annotations filter (i.e variants will be returned if they have either the specified pathogenicity OR transcript consequence)',
})

export const HGMD_PATHOGENICITY_PANEL = pathogenicityPanel(true)
export const PATHOGENICITY_PANEL = pathogenicityPanel(false)

const ANNOTATION_GROUP_INDEX_MAP = ANNOTATION_GROUPS.reduce((acc, { name }, i) => ({ ...acc, [name]: i }), {})

export const annotationFieldLayout = (annotationGroups, hideOther) => fieldComponents => [
  ...annotationGroups.map(groups =>
    <Form.Field key={groups[0]} width={3}>
      {groups.map(group =>
        <div key={group}>
          {fieldComponents[ANNOTATION_GROUP_INDEX_MAP[group]]}
          <VerticalSpacer height={20} />
        </div>,
      )}
    </Form.Field>,
  ),
  !hideOther ? (
    <Form.Field key={VEP_GROUP_OTHER} width={4}>
      {fieldComponents[ANNOTATION_GROUP_INDEX_MAP[VEP_GROUP_OTHER]]}
    </Form.Field>
  ) : null,
].filter(fields => fields)

const MAX_FREQ_COMPONENTS_PER_ROW = 6

//Layout the frequency filter fields into two rows.
const freqFieldLayout = fieldComponents =>
  <Form.Field>
    <Form.Group widths="equal">
      {fieldComponents.slice(0, MAX_FREQ_COMPONENTS_PER_ROW)}
    </Form.Group>
    <Form.Group widths="equal">
      {// add empty fields to pad out the second row so the "equal" widths are the same
        Array.from({ length: (2 * MAX_FREQ_COMPONENTS_PER_ROW) - fieldComponents.length }, (x, i) => i).map(e =>
          <Form.Field key={e} />)
      }
      {fieldComponents.slice(MAX_FREQ_COMPONENTS_PER_ROW)}
    </Form.Group>
  </Form.Field>

export const ANNOTATION_PANEL = {
  name: 'annotations',
  headerProps: { title: 'Annotations', inputProps: JsonSelectPropsWithAll(ANNOTATION_FILTER_OPTIONS, ALL_ANNOTATION_FILTER_DETAILS) },
  fields: ANNOTATION_GROUPS,
  fieldProps: { control: AlignedCheckboxGroup, format: val => val || [] },
  fieldLayout: annotationFieldLayout([[VEP_GROUP_SV_CONSEQUENCES, VEP_GROUP_SV], HIGH_IMPACT_GROUPS_NO_SV, MODERATE_IMPACT_GROUPS, CODING_IMPACT_GROUPS]),
}

export const FREQUENCY_PANEL = {
  name: 'freqs',
  headerProps: {
    title: 'Frequency',
    inputSize: 10,
    inputProps: {
      component: HeaderFrequencyFilter,
      format: val => val || {},
    },
  },
  fields: FREQUENCIES,
  fieldProps: { control: FrequencyFilter, format: val => val || {} },
  fieldLayout: freqFieldLayout,
  helpText: 'Filter by allele frequency (popmax AF where available) or by allele count (AC). In applicable populations, also filter by homozygous/hemizygous count (H/H).',
}

export const LOCATION_PANEL = {
  name: 'locus',
  headerProps: { title: 'Location' },
  fields: LOCATION_FIELDS,
  helpText: 'Filter by variant location. Entries can be either gene symbols (e.g. CFTR) or intervals in the form <chrom>:<start>-<end> (e.g. 4:6935002-87141054) or separated by tab. Variant entries can be either rsIDs (e.g. rs61753695) or variants in the form <chrom>-<pos>-<ref>-<alt> (e.g. 4-88047328-C-T). Entries can be separated by commas or whitespace.',
}

export const QUALITY_PANEL = {
  name: 'qualityFilter',
  headerProps: { title: 'Call Quality', inputProps: JsonSelectPropsWithAll(QUALITY_FILTER_OPTIONS, ALL_QUALITY_FILTER) },
  fields: QUALITY_FILTER_FIELDS,
  fieldProps: { control: LabeledSlider, format: val => val || null },
}

const HeaderContent = React.memo(({ name, title, inputSize, inputProps }) =>
  <Grid>
    <Grid.Row>
      <Grid.Column width={inputSize ? 16 - inputSize : 8} verticalAlign="middle">{title}</Grid.Column>
      {inputProps &&
        <ToggleHeaderFieldColumn width={inputSize || 3} floated="right" textAlign="right" onClick={e => e.stopPropagation()}>
          {configuredField({ ...inputProps, name })}
        </ToggleHeaderFieldColumn>
      }
    </Grid.Row>
  </Grid>,
)

HeaderContent.propTypes = {
  title: PropTypes.string.isRequired,
  name: PropTypes.string,
  inputSize: PropTypes.number,
  inputProps: PropTypes.object,
}

const PanelContent = React.memo(({ name, fields, fieldProps, helpText, fieldLayout }) => {
  const fieldComponents = fields && configuredFields({ fields: fields.map(field => ({ ...(fieldProps || {}), ...field })) })
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
})

PanelContent.propTypes = {
  fields: PropTypes.array,
  name: PropTypes.string.isRequired,
  fieldProps: PropTypes.object,
  helpText: PropTypes.node,
  fieldLayout: PropTypes.func,
}

class VariantSearchFormPanels extends React.PureComponent {
  state = { active: {} }

  expandAll = (e) => {
    e.preventDefault()
    this.setState({ active: this.props.panels.reduce((acc, { name }) => ({ ...acc, [name]: true }), {}) })
  }

  collapseAll = (e) => {
    e.preventDefault()
    this.setState({ active: {} })
  }

  handleTitleClick = name => () => {
    const { active } = this.state
    this.setState({ active: { ...active, [name]: !active[name] } })
  }


  render() {
    return (
      <div>
        <ExpandCollapseCategoryContainer>
          <ButtonLink onClick={this.expandAll}>Expand All &nbsp;<Icon name="plus" /></ButtonLink>
          <b>| &nbsp;&nbsp;</b>
          <ButtonLink onClick={this.collapseAll}>Collapse All &nbsp;<Icon name="minus" /></ButtonLink>
        </ExpandCollapseCategoryContainer>
        <VerticalSpacer height={10} />
        <FormSection name="search">
          <Accordion fluid exclusive={false}>
            {this.props.panels.reduce((acc, { name, headerProps, ...panelContentProps }, i) => {
              const isActive = !!this.state.active[name]
              let attachedTitle = true
              if (i === 0) {
                attachedTitle = 'top'
              } else if (i === this.props.panels.length - 1 && !isActive) {
                attachedTitle = 'bottom'
              }
              return [...acc,
                <Accordion.Title
                  key={`${name}-title`}
                  active={isActive}
                  index={i}
                  onClick={this.handleTitleClick(name)}
                  as={ToggleHeader}
                  attached={attachedTitle}
                >
                  <Icon name="dropdown" />
                  <HeaderContent name={name} {...headerProps} />
                </Accordion.Title>,
                <Accordion.Content
                  key={`${name}-content`}
                  active={isActive}
                  as={Segment}
                  attached={i === this.props.panels.length - 1 ? 'bottom' : true}
                  padded
                  textAlign="center"
                >
                  <PanelContent name={name} {...panelContentProps} />
                </Accordion.Content>,
              ] }, [])
            }
          </Accordion>
        </FormSection>
      </div>
    )
  }
}

VariantSearchFormPanels.propTypes = {
  panels: PropTypes.array,
}

export default VariantSearchFormPanels
