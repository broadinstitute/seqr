import React from 'react'
import styled from 'styled-components'
import { Form, Header, Grid, Loader, Table, List } from 'semantic-ui-react'

import { ButtonLink } from 'shared/components/StyledComponents'
import { CreateLocusListButton } from 'shared/components/buttons/LocusListButtons'
import { Select, AlignedCheckboxGroup, AlignedBooleanCheckbox } from 'shared/components/form/Inputs'
import Modal from 'shared/components/modal/Modal'
import { camelcaseToTitlecase } from 'shared/utils/stringUtils'
import {
  SV_IN_SILICO_GROUP,
  NO_SV_IN_SILICO_GROUPS,
  ALL_INHERITANCE_FILTER,
  DATASET_TYPE_SNV_INDEL_CALLS,
  DATASET_TYPE_SV_CALLS,
  DATASET_TYPE_MITO_CALLS,
  LOCUS_LIST_ITEMS_FIELD,
  PANEL_APP_CONFIDENCE_LEVELS,
} from 'shared/utils/constants'

import {
  FREQUENCIES,
  IN_SILICO_FIELDS,
  QUALITY_FILTER_FIELDS,
  QUALITY_FILTER_OPTIONS,
  ALL_QUALITY_FILTER,
  IN_SILICO_GROUP_INDEX_MAP,
  IN_SILICO_SPLICING_FIELD,
  SNP_FREQUENCIES, SNP_QUALITY_FILTER_FIELDS,
  MITO_FREQUENCIES, MITO_QUALITY_FILTER_FIELDS, SV_FREQUENCIES, SV_QUALITY_FILTER_FIELDS,
} from 'shared/components/panel/search/constants'

import {
  INHERITANCE_FILTER_JSON_OPTIONS,
  INHERITANCE_FILTER_LOOKUP,
  INHERITANCE_MODE_LOOKUP,
  NUM_ALT_OPTIONS,
  HGMD_PATHOGENICITY_FILTER_OPTIONS,
  ANY_PATHOGENICITY_FILTER,
  PATHOGENICITY_FIELDS,
  PATHOGENICITY_FILTER_OPTIONS,
  ANNOTATION_FILTER_OPTIONS,
  ALL_ANNOTATION_FILTER_DETAILS,
  ALL_CODING_IMPACT_GROUPS,
  SV_GROUPS,
  SV_GROUPS_NO_NEW,
  VARIANT_ANNOTATION_LAYOUT_GROUPS,
  ANNOTATION_GROUPS,
  LOCUS_FIELD_NAME,
  PANEL_APP_FIELD_NAME,
} from '../constants'
import LocusListSelector from './filters/LocusListSelector'
import LocusListItemsFilter from './filters/LocusListItemsFilter'
import PaMoiSelector from './filters/PaMoiSelector'
import PaLocusListSelector from './filters/PaLocusListSelector'
import CustomInheritanceFilter from './filters/CustomInheritanceFilter'
import { FrequencyFilter, HeaderFrequencyFilter } from './filters/FrequencyFilter'

const LabeledSlider = React.lazy(() => import('./filters/LabeledSlider'))

const CenteredTable = styled(Table)`
  margin-left: auto !important;
  margin-right: auto !important;
`

const BaseDetailLink = styled(ButtonLink)`
  &.ui.button.basic {
    margin-left: .2em;
    margin-right: 0;
    font-weight: initial;
    font-style: inherit;
  }
`
const DetailLink = props => <BaseDetailLink {...props} />

const LazyLabeledSlider = props => <React.Suspense fallback={<Loader />}><LabeledSlider {...props} /></React.Suspense>

export const JsonSelectPropsWithAll = (options, all) => ({
  component: Select,
  format: val => JSON.stringify(val) || JSON.stringify(all.value),
  parse: val => JSON.parse(val),
  options: options.map(({ value, ...option }) => ({ ...option, value: JSON.stringify(value) })),
})

const DATASET_TYPE_VARIANT_MITO = `${DATASET_TYPE_MITO_CALLS},${DATASET_TYPE_SNV_INDEL_CALLS}`
const DATASET_TYPE_VARIANT_SV = `${DATASET_TYPE_SV_CALLS},${DATASET_TYPE_SNV_INDEL_CALLS}`

export const PATHOGENICITY_PANEL_NAME = 'pathogenicity'
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
export const HGMD_HEADER_INPUT_PROPS = JsonSelectPropsWithAll(
  HGMD_PATHOGENICITY_FILTER_OPTIONS, ANY_PATHOGENICITY_FILTER,
)

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

const ANNOTATION_GROUPS_SPLICE = [...ANNOTATION_GROUPS, IN_SILICO_SPLICING_FIELD]
const ANNOTATION_GROUP_INDEX_MAP = ANNOTATION_GROUPS_SPLICE.reduce((acc, { name }, i) => ({ ...acc, [name]: i }), {})

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

export const ANNOTATION_SECONDARY_NAME = 'annotations_secondary'
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

const VARIANT_FIELD_NAME = 'rawVariantItems'
const SELECTED_MOIS_FIELD_NAME = 'selectedMOIs'
const PANEL_APP_COLORS = [...new Set(
  Object.entries(PANEL_APP_CONFIDENCE_LEVELS).sort((a, b) => b[0] - a[0]).map(config => config[1]),
)]
const LOCATION_FIELDS = [
  {
    name: LOCUS_LIST_ITEMS_FIELD.name,
    label: LOCUS_LIST_ITEMS_FIELD.label,
    labelHelp: LOCUS_LIST_ITEMS_FIELD.labelHelp,
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
  {
    name: 'excludeLocations',
    component: LocusListItemsFilter,
    filterComponent: AlignedBooleanCheckbox,
    label: 'Exclude locations',
    labelHelp: 'Search for variants not in the specified genes/ intervals',
    width: 10,
    shouldDisable: locus => !!locus[VARIANT_FIELD_NAME],
  },
]

const LOCATION_PANEL = {
  name: LOCUS_FIELD_NAME,
  headerProps: { title: 'Location' },
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

const INHERITANCE_PANEL = {
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

const LOCATION_PANEL_WITH_GENE_LIST = {
  ...LOCATION_PANEL,
  headerProps: {
    title: 'Location',
    name: 'locus',
    inputSize: 5,
    inputProps: { component: LocusListSelector, format: val => val || {} },
  },
}

export const PANELS = [
  INHERITANCE_PANEL,
  PATHOGENICITY_PANEL,
  ANNOTATION_PANEL,
  ANNOTATION_SECONDARY_PANEL,
  IN_SILICO_PANEL,
  FREQUENCY_PANEL,
  LOCATION_PANEL_WITH_GENE_LIST,
  QUALITY_PANEL,
]
