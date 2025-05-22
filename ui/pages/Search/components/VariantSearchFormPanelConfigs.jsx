import React from 'react'
import styled from 'styled-components'
import { Form, Grid, Header, List, Loader, Table } from 'semantic-ui-react'

import { ButtonLink } from 'shared/components/StyledComponents'
import { CreateLocusListButton } from 'shared/components/buttons/LocusListButtons'
import { Select, AlignedBooleanCheckbox, AlignedCheckboxGroup, RadioGroup, InlineToggle } from 'shared/components/form/Inputs'
import Modal from 'shared/components/modal/Modal'
import { snakecaseToTitlecase, camelcaseToTitlecase } from 'shared/utils/stringUtils'
import {
  LOCUS_LIST_ITEMS_FIELD,
  PANEL_APP_CONFIDENCE_LEVELS,
  ORDERED_PREDICTOR_FIELDS,
  FREQUENCIES,
  SNP_FREQUENCIES,
  MITO_FREQUENCIES,
  SV_FREQUENCIES,
  THIS_CALLSET_FREQUENCY,
  SPLICE_AI_FIELD,
  SV_IN_SILICO_GROUP,
  NO_SV_IN_SILICO_GROUPS,
  DATASET_TYPE_SNV_INDEL_CALLS,
  DATASET_TYPE_SV_CALLS,
  DATASET_TYPE_MITO_CALLS,
  predictorColorRanges,
} from 'shared/utils/constants'

import {
  ALL_ANNOTATION_FILTER_DETAILS, ALL_CODING_IMPACT_GROUPS,
  ALL_INHERITANCE_FILTER, ALL_QUALITY_FILTER,
  ANNOTATION_FILTER_OPTIONS,
  ANNOTATION_GROUPS,
  ANY_PATHOGENICITY_FILTER,
  HGMD_PATHOGENICITY_FILTER_OPTIONS,
  INHERITANCE_FILTER_JSON_OPTIONS,
  INHERITANCE_FILTER_LOOKUP,
  INHERITANCE_MODE_LOOKUP, LOCUS_FIELD_NAME,
  NUM_ALT_OPTIONS,
  PANEL_APP_FIELD_NAME,
  CLINVAR_FIELD,
  PATHOGENICITY_FIELDS,
  PATHOGENICITY_FILTER_OPTIONS, QUALITY_FILTER_OPTIONS, SV_GROUPS, SV_GROUPS_NO_NEW, VARIANT_ANNOTATION_LAYOUT_GROUPS,
} from '../constants'
import LocusListItemsFilter from './filters/LocusListItemsFilter'
import PaMoiSelector from './filters/PaMoiSelector'
import PaLocusListSelector from './filters/PaLocusListSelector'
import CustomInheritanceFilter from './filters/CustomInheritanceFilter'
import { FrequencyFilter, HeaderFrequencyFilter } from './filters/FrequencyFilter'
import LocusListSelector from './filters/LocusListSelector'

const LabeledSlider = React.lazy(() => import('./filters/LabeledSlider'))

const BaseDetailLink = styled(ButtonLink)`
  &.ui.button.basic {
    margin-left: .2em;
    margin-right: 0;
    font-weight: initial;
    font-style: inherit;
  }
`
const DetailLink = props => <BaseDetailLink {...props} />

const REQUIRE_SCORE_FIELD = {
  name: 'requireScore',
  component: AlignedBooleanCheckbox,
  label: 'Require Filtered Predictor',
  labelHelp: 'Only return variants where at least one filtered predictor is present. By default, variants are returned if a predictor meets the filtered value or is missing entirely',
}

export const IN_SILICO_FIELDS = [
  REQUIRE_SCORE_FIELD,
  ...ORDERED_PREDICTOR_FIELDS.filter(({ displayOnly }) => !displayOnly).map(
    ({ field, fieldTitle, thresholds, reverseThresholds, indicatorMap, group, min, max, requiresCitation }) => {
      const label = fieldTitle || snakecaseToTitlecase(field)
      const filterField = { name: field, label, group }

      if (indicatorMap) {
        return {
          labelHelp: `Select a value for ${label}`,
          component: Select,
          options: [
            { text: '', value: null },
            ...Object.entries(indicatorMap).map(([val, { value, ...opt }]) => ({ value: val, text: value, ...opt })),
          ],
          ...filterField,
        }
      }

      const labelHelp = (
        <div>
          {`Enter a numeric cutoff for ${label}`}
          {thresholds && predictorColorRanges(thresholds, requiresCitation, reverseThresholds)}
        </div>
      )
      return {
        labelHelp,
        control: Form.Input,
        type: 'number',
        min: min || 0,
        max: max || 1,
        step: max ? 1 : 0.05,
        ...filterField,
      }
    },
  )]

const VARIANT_FIELD_NAME = 'rawVariantItems'
const SELECTED_MOIS_FIELD_NAME = 'selectedMOIs'
const PANEL_APP_COLORS = [...new Set(
  Object.entries(PANEL_APP_CONFIDENCE_LEVELS).sort((a, b) => b[0] - a[0]).map(config => config[1]),
)]
const BASE_LOCUS_FIELD = {
  name: LOCUS_LIST_ITEMS_FIELD.name,
  label: LOCUS_LIST_ITEMS_FIELD.label,
  labelHelp: LOCUS_LIST_ITEMS_FIELD.labelHelp,
}
export const LOCATION_FIELDS = [
  {
    ...BASE_LOCUS_FIELD,
    component: LocusListItemsFilter,
    width: 9,
    shouldShow: locus => !locus[PANEL_APP_FIELD_NAME],
    shouldDisable: locus => !!locus[VARIANT_FIELD_NAME],
  },
  ...PANEL_APP_COLORS.map(color => ({
    key: color,
    name: `${PANEL_APP_FIELD_NAME}.${color}`,
    iconColor: color,
    label: color === 'none' ? 'Genes' : `${camelcaseToTitlecase(color)} Genes`,
    labelHelp: 'A list of genes, can be separated by commas or whitespace',
    component: LocusListItemsFilter,
    filterComponent: PaLocusListSelector,
    width: 3,
    shouldShow: locus => !!locus[PANEL_APP_FIELD_NAME],
    shouldDisable: locus => !!locus[VARIANT_FIELD_NAME],
    color,
  })),
  {
    name: VARIANT_FIELD_NAME,
    label: 'Variants',
    labelHelp: 'A list of variants. Can be separated by commas or whitespace. Variants can be represented by rsID or in the form <chrom>-<pos>-<ref>-<alt>',
    component: LocusListItemsFilter,
    width: 4,
    shouldDisable: locus => !!locus[LOCUS_LIST_ITEMS_FIELD.name] || !!locus[PANEL_APP_FIELD_NAME],
  },
  {
    name: SELECTED_MOIS_FIELD_NAME,
    label: 'Modes of Inheritance',
    labelHelp: 'Filter the Gene List based on Modes of Inheritance from Panel App',
    component: LocusListItemsFilter,
    filterComponent: PaMoiSelector,
    width: 6,
    shouldDisable: locus => !!locus[VARIANT_FIELD_NAME],
    shouldShow: locus => !!locus[PANEL_APP_FIELD_NAME],
  },
  {
    name: 'create',
    fullFieldValue: true,
    component: LocusListItemsFilter,
    control: CreateLocusListButton,
    width: 4,
    shouldShow: locus => !locus[PANEL_APP_FIELD_NAME],
    shouldDisable: locus => !locus[LOCUS_LIST_ITEMS_FIELD.name],
  },
]

export const SNP_QUALITY_FILTER_FIELDS = [
  {
    name: 'affected_only',
    label: 'Affected Only',
    labelHelp: 'Only apply quality filters to affected individuals',
    control: InlineToggle,
    color: 'grey',
    width: 6,
  },
  {
    name: 'vcf_filter',
    label: 'Filter Value',
    labelHelp: 'Either show only variants that PASSed variant quality filters applied when the dataset was processed (typically VQSR or Hard Filters), or show all variants',
    control: RadioGroup,
    options: [{ value: '', text: 'Show All Variants' }, { value: 'pass', text: 'Pass Variants Only' }],
    margin: '1em 2em',
    widths: 'equal',
  },
  {
    name: 'min_gq',
    label: 'Genotype Quality',
    labelHelp: 'Genotype Quality (GQ) is a statistical measure of confidence in the genotype call (eg. hom. or het) based on the read data',
    min: 0,
    max: 100,
    step: 5,
  },
  {
    name: 'min_ab',
    label: 'Allele Balance',
    labelHelp: 'The allele balance represents the percentage of reads that support the alt allele out of the total number of sequencing reads overlapping a variant. Use this filter to set a minimum percentage for the allele balance in heterozygous individuals.',
    min: 0,
    max: 50,
    step: 5,
  },
]

const DividedFormField = styled(Form.Field)`
  border-left: solid grey 1px;
`

export const MITO_QUALITY_FILTER_FIELDS = [
  {
    name: 'min_hl',
    label: 'Heteroplasmy level',
    labelHelp: 'Heteroplasmy level (HL) is the percentage of the alt alleles out of all alleles.',
    min: 0,
    max: 50,
    step: 5,
    component: DividedFormField,
  },
]

export const SV_QUALITY_FILTER_FIELDS = [
  {
    name: 'min_qs',
    label: 'WES SV Quality Score',
    labelHelp: 'The quality score (QS) represents the quality of a Structural Variant call. Recommended SV-QS cutoffs for filtering: duplication >= 50, deletion >= 100, homozygous deletion >= 400.',
    min: 0,
    max: 1000,
    step: 10,
    component: DividedFormField,
  },
  {
    name: 'min_gq_sv',
    label: 'WGS SV Genotype Quality',
    labelHelp: 'The genotype quality (GQ) represents the quality of a Structural Variant call. Recommended SV-GQ cutoffs for filtering: > 10.',
    min: 0,
    max: 100,
    step: 5,
  },
]

export const QUALITY_FILTER_FIELDS = [
  ...SNP_QUALITY_FILTER_FIELDS,
  ...MITO_QUALITY_FILTER_FIELDS,
  ...SV_QUALITY_FILTER_FIELDS,
]

export const INHERITANCE_PANEL = {
  name: 'inheritance',
  headerProps: {
    title: 'Inheritance',
    inputProps: {
      component: Select,
      options: INHERITANCE_FILTER_JSON_OPTIONS,
      format: (val) => {
        if (!(val || {}).filter) {
          return ALL_INHERITANCE_FILTER
        }
        if (val.filter.genotype) {
          return null
        }
        const { affected, genotype, ...coreFilter } = val.filter
        return INHERITANCE_MODE_LOOKUP[val.mode] || INHERITANCE_MODE_LOOKUP[JSON.stringify(coreFilter)]
      },
      parse: val => (val === ALL_INHERITANCE_FILTER ? null : {
        mode: val,
        filter: INHERITANCE_FILTER_LOOKUP[val],
      }),
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
        <i>seqr</i>
        implements the following set of standard Mendelian inheritance methods to identify variants that
        segregate with a phenotype in a family
        {INHERITANCE_FILTER_JSON_OPTIONS.filter(({ value }) => value !== ALL_INHERITANCE_FILTER).map(
          ({ value, text, detail }) => <Header key={value} content={text} subheader={detail} />,
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
      </Modal>
      ) or specify custom alternate allele counts. You can also specify the affected status for an individual
      that differs from the status in the pedigree.
    </span>
  ),
}

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

export const PATHOGENICITY_PANEL_NAME = 'pathogenicity'
const PATHOGENICITY_FIELD_PROPS = { control: AlignedCheckboxGroup, format: val => val || [] }
export const PATHOGENICITY_PANEL = {
  name: PATHOGENICITY_PANEL_NAME,
  headerProps: {
    title: 'Pathogenicity',
    inputProps: JsonSelectPropsWithAll(PATHOGENICITY_FILTER_OPTIONS, ANY_PATHOGENICITY_FILTER),
  },
  fields: PATHOGENICITY_FIELDS,
  fieldProps: PATHOGENICITY_FIELD_PROPS,
  helpText: 'Filter by reported pathogenicity.  This overrides the annotation filter, the frequency filter, and the call quality filter.  Variants will be returned if they have the specified transcript consequence AND the specified frequencies AND all individuals pass all specified quality filters OR if the variant has the specified pathogenicity and a frequency up to 0.05.',
}
export const HGMD_HEADER_INPUT_PROPS = JsonSelectPropsWithAll(
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

export const ANNOTATION_PANEL = {
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

export const ANNOTATION_SECONDARY_NAME = 'annotations_secondary'
export const ANNOTATION_SECONDARY_PANEL = {
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

const NO_ES_SNP_FREQUENCIES = [
  ...SNP_FREQUENCIES.slice(0, -1),
  {
    name: THIS_CALLSET_FREQUENCY,
    label: 'seqr',
    homHemi: true,
    skipAf: true,
    labelHelp: 'Filter by allele count (AC) across all the samples in seqr.',
  },
]

export const FREQUENCY_PANEL = {
  name: 'freqs',
  headerProps: {
    title: 'Frequency',
    inputSize: 11,
    inputProps: {
      component: HeaderFrequencyFilter,
      format: val => val || {},
    },
  },
  esEnabledFields: FREQUENCIES,
  fields: [...NO_ES_SNP_FREQUENCIES, ...MITO_FREQUENCIES, ...SV_FREQUENCIES],
  datasetTypeFields: {
    [DATASET_TYPE_SNV_INDEL_CALLS]: NO_ES_SNP_FREQUENCIES,
    [DATASET_TYPE_VARIANT_MITO]: NO_ES_SNP_FREQUENCIES.concat(MITO_FREQUENCIES),
    [DATASET_TYPE_VARIANT_SV]: NO_ES_SNP_FREQUENCIES.concat(SV_FREQUENCIES),
  },
  esEnabledDatasetTypeFields: {
    [DATASET_TYPE_SNV_INDEL_CALLS]: SNP_FREQUENCIES,
    [DATASET_TYPE_VARIANT_MITO]: SNP_FREQUENCIES.concat(MITO_FREQUENCIES),
    [DATASET_TYPE_VARIANT_SV]: SNP_FREQUENCIES.concat(SV_FREQUENCIES),
  },
  fieldProps: {
    control: FrequencyFilter,
    format: val => val || {},
  },
  fieldLayout: freqFieldLayout,
  helpText: 'Filter by allele frequency (popmax AF where available) or by allele count (AC). In applicable populations, also filter by homozygous/hemizygous count (H/H).',
}

export const LOCATION_PANEL = {
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

export const IN_SILICO_PANEL = {
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

export const QUALITY_PANEL = {
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

const ES_EXCLUDE_FIELDS = [
  {
    ...BASE_LOCUS_FIELD,
    component: Form.TextArea,
    rows: 8,
  },
]
const EXCLUDE_FIELDS = [
  {
    ...CLINVAR_FIELD,
    ...PATHOGENICITY_FIELD_PROPS,
    width: 8,
  },
  ...ES_EXCLUDE_FIELDS,
]

export const EXCLUDE_PANEL = {
  name: 'exclude',
  headerProps: { title: 'Exclude' },
  fields: EXCLUDE_FIELDS,
  esEnabledFields: ES_EXCLUDE_FIELDS,
  helpText: 'Exclude variants from the search results based on the specified criteria. This filter will override any other filters applied.',
}
