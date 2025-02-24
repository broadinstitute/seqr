import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { FormSpy } from 'react-final-form'
import styled from 'styled-components'
import { Form, Accordion, Header, Segment, Grid, Icon, Loader, Table } from 'semantic-ui-react'

import { getElasticsearchEnabled } from 'redux/selectors'
import { VerticalSpacer } from 'shared/components/Spacers'
import { ButtonLink } from 'shared/components/StyledComponents'
import { Select, AlignedCheckboxGroup } from 'shared/components/form/Inputs'
import { configuredField, configuredFields } from 'shared/components/form/FormHelpers'
import {
  FREQUENCIES,
  SNP_FREQUENCIES,
  MITO_FREQUENCIES,
  SV_FREQUENCIES,
  SPLICE_AI_FIELD,
  SV_IN_SILICO_GROUP,
  NO_SV_IN_SILICO_GROUPS,
  DATASET_TYPE_SNV_INDEL_CALLS,
  DATASET_TYPE_SV_CALLS,
  DATASET_TYPE_MITO_CALLS,
} from 'shared/utils/constants'

import { FrequencyFilter, HeaderFrequencyFilter } from './filters/FrequencyFilter'
import LocusListSelector from './filters/LocusListSelector'
import {
  IN_SILICO_FIELDS,
  QUALITY_FILTER_FIELDS,
  SNP_QUALITY_FILTER_FIELDS,
  MITO_QUALITY_FILTER_FIELDS,
  SV_QUALITY_FILTER_FIELDS,
  LOCATION_FIELDS,
  INHERITANCE_PANEL,
} from './VariantSearchFormPanelConfigs'
import {
  HGMD_PATHOGENICITY_FIELDS,
  HGMD_PATHOGENICITY_FILTER_OPTIONS,
  ANY_PATHOGENICITY_FILTER,
  ANNOTATION_GROUPS,
  ANNOTATION_FILTER_OPTIONS,
  ALL_ANNOTATION_FILTER_DETAILS,
  QUALITY_FILTER_OPTIONS,
  ALL_QUALITY_FILTER,
  ALL_CODING_IMPACT_GROUPS,
  SV_GROUPS,
  LOCUS_FIELD_NAME,
  ALL_RECESSIVE_INHERITANCE_FILTERS,
  PATHOGENICITY_FIELDS,
  PATHOGENICITY_FILTER_OPTIONS,
  SV_GROUPS_NO_NEW,
  VARIANT_ANNOTATION_LAYOUT_GROUPS,
} from '../constants'
import { getDatasetTypes, getHasHgmdPermission } from '../selectors'

const LabeledSlider = React.lazy(() => import('./filters/LabeledSlider'))

const ToggleHeader = styled(Header).attrs({ size: 'huge', block: true })`
  margin-top: 0px !important;

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
    
    >.icon {
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

const CenteredTable = styled(Table)`
  margin-left: auto !important;
  margin-right: auto !important;
`

const LazyLabeledSlider = props => <React.Suspense fallback={<Loader />}><LabeledSlider {...props} /></React.Suspense>

const JsonSelectPropsWithAll = (options, all) => ({
  component: Select,
  format: val => JSON.stringify(val) || JSON.stringify(all.value),
  parse: val => JSON.parse(val),
  options: options.map(({ value, ...option }) => ({ ...option, value: JSON.stringify(value) })),
})

const PATHOGENICITY_PANEL_NAME = 'pathogenicity'
const PATHOGENICITY_PANEL = {
  name: PATHOGENICITY_PANEL_NAME,
  headerProps: {
    title: 'Pathogenicity',
    inputProps: JsonSelectPropsWithAll(PATHOGENICITY_FILTER_OPTIONS, ANY_PATHOGENICITY_FILTER),
  },
  fields: PATHOGENICITY_FIELDS,
  fieldProps: { control: AlignedCheckboxGroup, format: val => val || [] },
  helpText: 'Filter by reported pathogenicity.  This overrides the annotation filter, the frequency filter, and the call quality filter.  Variants will be returned if they have the specified transcript consequence AND the specified frequencies AND all individuals pass all specified quality filters OR if the variant has the specified pathogenicity and a frequency up to 0.05.',
}
const HGMD_HEADER_INPUT_PROPS = JsonSelectPropsWithAll(
  HGMD_PATHOGENICITY_FILTER_OPTIONS, ANY_PATHOGENICITY_FILTER,
)

const IN_SILICO_SPLICING_FIELD = IN_SILICO_FIELDS.find(({ name }) => name === SPLICE_AI_FIELD)
const IN_SILICO_GROUP_INDEX_MAP = IN_SILICO_FIELDS.reduce(
  (acc, { group }, i) => ({ ...acc, [group]: [...(acc[group] || []), i] }), {},
)

const ANNOTATION_GROUPS_SPLICE = [...ANNOTATION_GROUPS, IN_SILICO_SPLICING_FIELD]
const ANNOTATION_GROUP_INDEX_MAP = ANNOTATION_GROUPS_SPLICE.reduce((acc, { name }, i) => ({ ...acc, [name]: i }), {})

const inSilicoFieldLayout = ([requireComponent, ...fieldComponents], groups) => (
  <Form.Field>
    <Grid divided="vertically">
      {groups.map(group => (
        <Grid.Row key={group}>
          <Grid.Column width={2} verticalAlign="middle"><Header size="small" content={group} /></Grid.Column>
          <Grid.Column width={14}>
            <Grid>
              <Grid.Row>
                {IN_SILICO_GROUP_INDEX_MAP[group].map(
                  i => <Grid.Column key={i} width={3}>{fieldComponents[i - 1]}</Grid.Column>,
                )}
              </Grid.Row>
            </Grid>
          </Grid.Column>
        </Grid.Row>
      ))}
      <Grid.Row>
        <Grid.Column>{requireComponent}</Grid.Column>
      </Grid.Row>
    </Grid>
  </Form.Field>
)

const annotationColSpan = ({ maxOptionsPerColumn, options = [] }) => Math.ceil(options.length / maxOptionsPerColumn)

const annotationGroupDisplay = component => (
  <Table.Cell colSpan={annotationColSpan(component.props)} content={component} />
)

const annotationFieldLayout = (fieldComponents, annotationGroups) => (
  <Form.Field>
    <CenteredTable basic="very" collapsing>
      {annotationGroups.map(groups => (
        <Table.Row key={groups[0]} verticalAlign="top">
          {groups.map(group => annotationGroupDisplay(fieldComponents[ANNOTATION_GROUP_INDEX_MAP[group]]))}
        </Table.Row>
      ))}
    </CenteredTable>
  </Form.Field>
)

const MAX_FREQ_COMPONENTS_PER_ROW = 4

// Layout the frequency filter fields into two rows.
const freqFieldLayout = fieldComponents => (
  <Form.Field>
    <Form.Group widths="equal">
      {fieldComponents.slice(0, MAX_FREQ_COMPONENTS_PER_ROW)}
    </Form.Group>
    <Form.Group widths="equal">
      {// add empty fields to pad out the second row so the "equal" widths are the same
        Array.from({ length: (2 * MAX_FREQ_COMPONENTS_PER_ROW) - fieldComponents.length }, (x, i) => i).map(
          e => <Form.Field key={e} />,
        )
      }
      {fieldComponents.slice(MAX_FREQ_COMPONENTS_PER_ROW)}
    </Form.Group>
  </Form.Field>
)

const DATASET_TYPE_VARIANT_MITO = `${DATASET_TYPE_MITO_CALLS},${DATASET_TYPE_SNV_INDEL_CALLS}`
const DATASET_TYPE_VARIANT_SV = `${DATASET_TYPE_SV_CALLS},${DATASET_TYPE_SNV_INDEL_CALLS}`

const ANNOTATION_PANEL = {
  name: 'annotations',
  headerProps: { title: 'Annotations', inputProps: JsonSelectPropsWithAll(ANNOTATION_FILTER_OPTIONS, ALL_ANNOTATION_FILTER_DETAILS) },
  fields: ANNOTATION_GROUPS_SPLICE,
  fieldProps: { control: AlignedCheckboxGroup, maxOptionsPerColumn: 7, format: val => val || [] },
  fieldLayout: annotationFieldLayout,
  fieldLayoutInput: [...VARIANT_ANNOTATION_LAYOUT_GROUPS, SV_GROUPS],
  datasetTypeFieldLayoutInput: {
    [DATASET_TYPE_SNV_INDEL_CALLS]: VARIANT_ANNOTATION_LAYOUT_GROUPS,
    [DATASET_TYPE_VARIANT_MITO]: VARIANT_ANNOTATION_LAYOUT_GROUPS,
  },
  noPadding: true,
  helpText: 'Filter by reported annotation. Variants will be returned if they have ANY of the specified annotations, including if they have a Splice AI score above the threshold and no other annotations. This filter is overridden by the pathogenicity filter, so variants will be returned if they have the specified pathogenicity even if none of the annotation filters match.',
}

const ANNOTATION_SECONDARY_NAME = 'annotations_secondary'
const ANNOTATION_SECONDARY_PANEL = {
  ...ANNOTATION_PANEL,
  headerProps: { ...ANNOTATION_PANEL.headerProps, title: 'Annotations (Second Hit)' },
  name: ANNOTATION_SECONDARY_NAME,
  helpText: (
    <span>
      Apply a secondary annotation filter to compound heterozygous pairs. All pairs of variants will include exactly one
      variant that matches the above annotation filter and one variant that matches this secondary annotation filter.
      <br />
      For recessive searches, homozygous and X-linked recessive variants will be filtered using the above main
      annotations filter.
    </span>
  ),
  fieldLayoutInput: [...ALL_CODING_IMPACT_GROUPS, SV_GROUPS_NO_NEW],
  datasetTypeFieldLayoutInput: {
    [DATASET_TYPE_SNV_INDEL_CALLS]: ALL_CODING_IMPACT_GROUPS,
    [DATASET_TYPE_VARIANT_MITO]: ALL_CODING_IMPACT_GROUPS,
  },
}

const FREQUENCY_PANEL = {
  name: 'freqs',
  headerProps: {
    title: 'Frequency',
    inputSize: 12,
    inputProps: {
      component: HeaderFrequencyFilter,
      format: val => val || {},
    },
  },
  fields: FREQUENCIES,
  datasetTypeFields: {
    [DATASET_TYPE_SNV_INDEL_CALLS]: SNP_FREQUENCIES,
    [DATASET_TYPE_VARIANT_MITO]: SNP_FREQUENCIES.concat(MITO_FREQUENCIES),
    [DATASET_TYPE_VARIANT_SV]: SNP_FREQUENCIES.concat(SV_FREQUENCIES),
  },
  fieldProps: {
    control: FrequencyFilter,
    format: val => val || {},
    formatNoEsLabel: label => label.replace('Callset', '').replace('This', 'seqr'),
  },
  fieldLayout: freqFieldLayout,
  helpText: 'Filter by allele frequency (popmax AF where available) or by allele count (AC). In applicable populations, also filter by homozygous/hemizygous count (H/H).',
}

const LOCATION_PANEL = {
  name: LOCUS_FIELD_NAME,
  headerProps: {
    title: 'Location',
    name: 'locus',
    inputSize: 5,
    inputProps: { component: LocusListSelector, format: val => val || {} },
  },
  fields: LOCATION_FIELDS,
  fieldLayout: fieldComponents => <Form.Field>{fieldComponents}</Form.Field>,
  helpText: 'Filter by variant location. Entries can be either gene symbols (e.g. CFTR) or intervals in the form <chrom>:<start>-<end> (e.g. 4:6935002-87141054) or separated by tab. Variant entries can be either rsIDs (e.g. rs61753695) or variants in the form <chrom>-<pos>-<ref>-<alt> (e.g. 10-129958997-T-C). Entries can be separated by commas or whitespace.',
}

const IN_SILICO_PANEL = {
  name: 'in_silico',
  headerProps: { title: 'In Silico Filters' },
  fields: IN_SILICO_FIELDS,
  fieldLayout: inSilicoFieldLayout,
  fieldLayoutInput: [...NO_SV_IN_SILICO_GROUPS, SV_IN_SILICO_GROUP],
  datasetTypeFieldLayoutInput: {
    [DATASET_TYPE_SNV_INDEL_CALLS]: NO_SV_IN_SILICO_GROUPS,
    [DATASET_TYPE_VARIANT_MITO]: NO_SV_IN_SILICO_GROUPS,
  },
  helpText: 'Filter by in-silico predictors. Variants matching any of the applied filters will be returned. For numeric filters, any variant with a score greater than or equal to the provided filter value will be returned.',
}

const QUALITY_PANEL = {
  name: 'qualityFilter',
  headerProps: { title: 'Call Quality', inputProps: JsonSelectPropsWithAll(QUALITY_FILTER_OPTIONS, ALL_QUALITY_FILTER) },
  fields: QUALITY_FILTER_FIELDS,
  datasetTypeFields: {
    [DATASET_TYPE_SNV_INDEL_CALLS]: SNP_QUALITY_FILTER_FIELDS,
    [DATASET_TYPE_VARIANT_MITO]: SNP_QUALITY_FILTER_FIELDS.concat(MITO_QUALITY_FILTER_FIELDS),
    [DATASET_TYPE_VARIANT_SV]: SNP_QUALITY_FILTER_FIELDS.concat(SV_QUALITY_FILTER_FIELDS),
  },
  fieldProps: { control: LazyLabeledSlider, format: val => val || null },
}

const PANELS = [
  INHERITANCE_PANEL,
  PATHOGENICITY_PANEL,
  ANNOTATION_PANEL,
  ANNOTATION_SECONDARY_PANEL,
  IN_SILICO_PANEL,
  FREQUENCY_PANEL,
  LOCATION_PANEL,
  QUALITY_PANEL,
]

const stopPropagation = e => e.stopPropagation()

const HeaderContent = React.memo(({ name, title, inputSize, inputProps, esEnabled }) => (
  <Grid>
    <Grid.Row>
      <Grid.Column width={inputSize ? 16 - inputSize : 8} verticalAlign="middle">{title}</Grid.Column>
      {inputProps && (
        <ToggleHeaderFieldColumn width={inputSize || 3} floated="right" textAlign="right" onClick={stopPropagation}>
          {configuredField({ ...inputProps, name: `search.${name}`, esEnabled })}
        </ToggleHeaderFieldColumn>
      )}
    </Grid.Row>
  </Grid>
))

HeaderContent.propTypes = {
  title: PropTypes.string.isRequired,
  name: PropTypes.string,
  inputSize: PropTypes.number,
  inputProps: PropTypes.object,
  esEnabled: PropTypes.bool,
}

const searchFieldName = (name, field) => (field.fullFieldValue ? `search.${name}` : `search.${name}.${field.name}`)

const formatField = (field, name, esEnabled, { formatNoEsLabel, ...fieldProps }) => ({
  ...fieldProps,
  ...field,
  name: searchFieldName(name, field),
  label: (!esEnabled && formatNoEsLabel) ? formatNoEsLabel(field.label) : field.label,
})

const PanelContent = React.memo(({
  name, fields, fieldProps, helpText, fieldLayout, fieldLayoutInput, esEnabled, noPadding, datasetTypes,
  datasetTypeFields, datasetTypeFieldLayoutInput,
}) => {
  const layoutInput = (datasetTypeFieldLayoutInput || {})[datasetTypes] || fieldLayoutInput
  const panelFields = (datasetTypeFields || {})[datasetTypes] || fields
  const fieldComponents = panelFields && configuredFields(
    { fields: panelFields.map(field => formatField(field, name, esEnabled, fieldProps || {})) },
  )
  return (
    <div>
      {helpText && (
        <i>
          {helpText}
          <VerticalSpacer height={20} />
        </i>
      )}
      <Form.Group widths="equal">
        {!noPadding && <Form.Field width={2} />}
        {fieldLayout ? fieldLayout(fieldComponents, layoutInput) : fieldComponents}
        {!noPadding && <Form.Field width={2} />}
      </Form.Group>
    </div>
  )
})

PanelContent.propTypes = {
  fields: PropTypes.arrayOf(PropTypes.object),
  name: PropTypes.string.isRequired,
  fieldProps: PropTypes.object,
  datasetTypes: PropTypes.string,
  datasetTypeFields: PropTypes.object,
  helpText: PropTypes.node,
  fieldLayout: PropTypes.func,
  fieldLayoutInput: PropTypes.arrayOf(PropTypes.string),
  datasetTypeFieldLayoutInput: PropTypes.object,
  esEnabled: PropTypes.bool,
  noPadding: PropTypes.bool,
}

const hasSecondaryAnnotation = inheritance => ALL_RECESSIVE_INHERITANCE_FILTERS.includes(inheritance?.mode)

class VariantSearchFormPanels extends React.PureComponent {

  static propTypes = {
    esEnabled: PropTypes.bool,
    hasHgmdPermission: PropTypes.bool,
    inheritance: PropTypes.string,
    datasetTypes: PropTypes.string,
  }

  state = { active: {} }

  expandAll = (e) => {
    e.preventDefault()
    this.setState({ active: PANELS.reduce((acc, { name }) => ({ ...acc, [name]: true }), {}) })
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
    const { esEnabled, hasHgmdPermission, inheritance, datasetTypes } = this.props
    const { active } = this.state
    return (
      <div>
        <ExpandCollapseCategoryContainer>
          <ButtonLink onClick={this.expandAll}>
            Expand All &nbsp;
            <Icon name="plus" />
          </ButtonLink>
          <b>| &nbsp;&nbsp;</b>
          <ButtonLink onClick={this.collapseAll}>
            Collapse All &nbsp;
            <Icon name="minus" />
          </ButtonLink>
        </ExpandCollapseCategoryContainer>
        <VerticalSpacer height={10} />
        <Accordion fluid exclusive={false}>
          {PANELS.reduce((acc, { name, headerProps, fields, ...panelContentProps }, i) => {
            if (name === ANNOTATION_SECONDARY_NAME && !hasSecondaryAnnotation(inheritance)) {
              return acc
            }
            const showHgmd = name === PATHOGENICITY_PANEL_NAME && hasHgmdPermission
            const isActive = !!active[name]
            let attachedTitle = true
            if (i === 0) {
              attachedTitle = 'top'
            } else if (i === PANELS.length - 1 && !isActive) {
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
                <HeaderContent
                  name={name}
                  esEnabled={esEnabled}
                  inputProps={showHgmd ? HGMD_HEADER_INPUT_PROPS : headerProps.inputProps}
                  {...headerProps}
                />
              </Accordion.Title>,
              <Accordion.Content
                key={`${name}-content`}
                active={isActive}
                as={Segment}
                attached={i === PANELS.length - 1 ? 'bottom' : true}
                padded
                textAlign="center"
              >
                <PanelContent
                  name={name}
                  esEnabled={esEnabled}
                  datasetTypes={datasetTypes}
                  fields={showHgmd ? HGMD_PATHOGENICITY_FIELDS : fields}
                  {...panelContentProps}
                />
              </Accordion.Content>,
            ]
          }, [])}
        </Accordion>
      </div>
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  hasHgmdPermission: getHasHgmdPermission(state, ownProps),
  datasetTypes: getDatasetTypes(state, ownProps),
  esEnabled: getElasticsearchEnabled(state),
})

const ConnectedVariantSearchFormPanels = connect(mapStateToProps)(VariantSearchFormPanels)

const SUBSCRIPTION = { values: true }

export default props => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => (
      <ConnectedVariantSearchFormPanels
        {...props}
        projectFamilies={values.projectFamilies}
        inheritance={values.search?.inheritance}
      />
    )}
  </FormSpy>
)
