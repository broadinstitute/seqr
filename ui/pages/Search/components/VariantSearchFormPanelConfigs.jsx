import React from 'react'
import styled from 'styled-components'
import { Form, Header, List } from 'semantic-ui-react'

import { ButtonLink } from 'shared/components/StyledComponents'
import { CreateLocusListButton } from 'shared/components/buttons/LocusListButtons'
import { Select, AlignedBooleanCheckbox, RadioGroup, InlineToggle } from 'shared/components/form/Inputs'
import Modal from 'shared/components/modal/Modal'
import { snakecaseToTitlecase, camelcaseToTitlecase } from 'shared/utils/stringUtils'
import {
  ALL_INHERITANCE_FILTER,
  LOCUS_LIST_ITEMS_FIELD,
  PANEL_APP_CONFIDENCE_LEVELS,
  ORDERED_PREDICTOR_FIELDS,
  predictorColorRanges,
} from 'shared/utils/constants'

import {
  INHERITANCE_FILTER_JSON_OPTIONS,
  INHERITANCE_FILTER_LOOKUP,
  INHERITANCE_MODE_LOOKUP,
  NUM_ALT_OPTIONS,
  PANEL_APP_FIELD_NAME,
} from '../constants'
import LocusListItemsFilter from './filters/LocusListItemsFilter'
import PaMoiSelector from './filters/PaMoiSelector'
import PaLocusListSelector from './filters/PaLocusListSelector'
import CustomInheritanceFilter from './filters/CustomInheritanceFilter'

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
export const LOCATION_FIELDS = [
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
