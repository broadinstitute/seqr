import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Header, List, Form, Grid } from 'semantic-ui-react'

import { getAnnotationSecondary } from 'redux/selectors'
import { ButtonLink } from 'shared/components/StyledComponents'
import { configuredField } from 'shared/components/form/ReduxFormWrapper'
import { Select } from 'shared/components/form/Inputs'
import Modal from 'shared/components/modal/Modal'
import VariantSearchFormPanels, {
  HGMD_PATHOGENICITY_PANEL, PATHOGENICITY_PANEL, ANNOTATION_PANEL, FREQUENCY_PANEL, LOCATION_PANEL, QUALITY_PANEL,
  annotationFieldLayout,
} from 'shared/components/panel/search/VariantSearchFormPanels'
import {
  HIGH_IMPACT_GROUPS_NO_SV, MODERATE_IMPACT_GROUPS, CODING_IMPACT_GROUPS, SV_CALLSET_FREQUENCY,
} from 'shared/components/panel/search/constants'
import { AfFilter } from 'shared/components/panel/search/FrequencyFilter'
import { ALL_INHERITANCE_FILTER, DATASET_TYPE_VARIANT_CALLS, DATASET_TYPE_SV_CALLS, VEP_GROUP_SV, VEP_GROUP_SV_CONSEQUENCES } from 'shared/utils/constants'
import { SavedSearchDropdown } from './SavedSearch'
import LocusListSelector from './filters/LocusListSelector'
import CustomInheritanceFilter from './filters/CustomInheritanceFilter'
import ProjectFamiliesField from './filters/ProjectFamiliesField'
import {
  INHERITANCE_FILTER_JSON_OPTIONS,
  INHERITANCE_FILTER_LOOKUP,
  INHERITANCE_MODE_LOOKUP,
  ALL_RECESSIVE_INHERITANCE_FILTERS,
  NUM_ALT_OPTIONS,
} from '../constants'
import { getDatasetTypes, getHasHgmdPermission } from '../selectors'

const SavedSearchColumn = styled(Grid.Column)`
  font-size: 0.75em;
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

const DividedFormField = styled(Form.Field)`
  border-left: solid grey 1px;
`

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
      options: INHERITANCE_FILTER_JSON_OPTIONS,
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
        { mode: val, filter: { affected: ((prevVal || {}).filter || {}).affected, ...INHERITANCE_FILTER_LOOKUP[val] }, annotationSecondary: ALL_RECESSIVE_INHERITANCE_FILTERS.includes(val) }),
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
        {INHERITANCE_FILTER_JSON_OPTIONS.filter(({ value }) => value !== ALL_INHERITANCE_FILTER).map(({ value, text, detail }) =>
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

const LOCATION_PANEL_WITH_GENE_LIST = {
  ...LOCATION_PANEL,
  headerProps: {
    title: 'Location',
    name: 'locus',
    inputSize: 5,
    inputProps: { component: LocusListSelector, format: val => val || {} },
  },
}

const ALL_DATASET_TYPE = `${DATASET_TYPE_SV_CALLS},${DATASET_TYPE_VARIANT_CALLS}`

const ANNOTATION_PANEL_MAP = {
  ...ANNOTATION_PANEL,
  [DATASET_TYPE_SV_CALLS]: {
    ...ANNOTATION_PANEL,
    fieldLayout: annotationFieldLayout([[VEP_GROUP_SV_CONSEQUENCES, VEP_GROUP_SV]], true),
  },
  [DATASET_TYPE_VARIANT_CALLS]: {
    ...ANNOTATION_PANEL,
    fieldLayout: annotationFieldLayout([HIGH_IMPACT_GROUPS_NO_SV, MODERATE_IMPACT_GROUPS, CODING_IMPACT_GROUPS]),
  },
}

const ANNOTATION_SECONDARY_NAME = 'annotations_secondary'
const secondaryPanel = panel => ({
  ...panel,
  headerProps: { ...panel.headerProps, title: 'Annotations (Second Hit)' },
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
})
const ANNOTATION_SECONDARY_PANEL_MAP = {
  ...secondaryPanel(ANNOTATION_PANEL),
  [DATASET_TYPE_SV_CALLS]: secondaryPanel(ANNOTATION_PANEL_MAP[DATASET_TYPE_SV_CALLS]),
  [DATASET_TYPE_VARIANT_CALLS]: secondaryPanel(ANNOTATION_PANEL_MAP[DATASET_TYPE_VARIANT_CALLS]),
}

const SVFrequecyHeaderFilter = ({ value, onChange }) =>
  <Form.Group inline>
    <AfFilter
      value={value[SV_CALLSET_FREQUENCY]}
      onChange={val => onChange({ ...value, [SV_CALLSET_FREQUENCY]: val })}
      inline
      label="Callset"
      width={16}
    />
  </Form.Group>

SVFrequecyHeaderFilter.propTypes = {
  value: PropTypes.any,
  onChange: PropTypes.func,
}

const QS_FILTER_FIELD = {
  name: 'min_qs',
  label: 'SV Quality Score',
  labelHelp: (
    <span>The quality score (QS) represents the quality of a Structural Variant call. Recommended SV-QS cutoffs for filtering:<br />
      WGS: &gt; 10; <br />
      WES: duplication &gt;= 50, deletion &gt;= 100, homozygous deletion &gt;= 400.
    </span>),
  min: 0,
  max: 1000,
  step: 10,
  component: DividedFormField,
}

const PANELS = [
  INHERITANCE_PANEL,
  {
    [DATASET_TYPE_SV_CALLS]: null,
    hasHgmdPermission: { [true]: HGMD_PATHOGENICITY_PANEL, [false]: PATHOGENICITY_PANEL },
  },
  ANNOTATION_PANEL_MAP,
  ANNOTATION_SECONDARY_PANEL_MAP,
  {
    ...FREQUENCY_PANEL,
    [DATASET_TYPE_VARIANT_CALLS]: {
      ...FREQUENCY_PANEL,
      fields: FREQUENCY_PANEL.fields.filter(({ name }) => name !== SV_CALLSET_FREQUENCY),
    },
    [DATASET_TYPE_SV_CALLS]: {
      ...FREQUENCY_PANEL,
      fields: FREQUENCY_PANEL.fields.filter(({ name }) => name === SV_CALLSET_FREQUENCY),
      headerProps: {
        ...FREQUENCY_PANEL.headerProps,
        inputSize: 3,
        inputProps: { component: SVFrequecyHeaderFilter },
      },
    },
  },
  LOCATION_PANEL_WITH_GENE_LIST,
  {
    ...QUALITY_PANEL,
    [ALL_DATASET_TYPE]: {
      ...QUALITY_PANEL,
      fields: [...QUALITY_PANEL.fields, QS_FILTER_FIELD],
    },
    [DATASET_TYPE_SV_CALLS]: {
      ...QUALITY_PANEL,
      fields: [QS_FILTER_FIELD],
    },
  },
]

const PANEL_MAP = [ALL_DATASET_TYPE, DATASET_TYPE_VARIANT_CALLS, DATASET_TYPE_SV_CALLS, ''].reduce((typeAcc, type) => {
  const typePanels = PANELS.map(panel => (panel[type] === undefined ? panel : panel[type])).filter(panel => panel)
  return {
    ...typeAcc,
    [type]: [true, false].reduce((analystAcc, hasHgmdBool) => {
      const analystPanels = typePanels.map(({ hasHgmdPermission, ...panel }) => (hasHgmdPermission === undefined ? panel : hasHgmdPermission[hasHgmdBool]))
      return {
        ...analystAcc,
        [hasHgmdBool]: [true, false].reduce((acc, annSecondaryBool) => ({
          ...acc,
          [annSecondaryBool]: annSecondaryBool ? analystPanels : analystPanels.filter(({ name }) => name !== ANNOTATION_SECONDARY_NAME),
        }), {}),
      } }, {}),
  }
}, {})

const VariantSearchFormContent = React.memo(({ hasHgmdPermission, displayAnnotationSecondary, datasetTypes }) => (
  <div>
    <ProjectFamiliesField />
    <Header size="huge" block>
      <Grid padded="horizontally" relaxed>
        <Grid.Row>
          <Grid.Column width={8} verticalAlign="middle">Select a Saved Search (Recommended)</Grid.Column>
          <SavedSearchColumn width={4} floated="right" textAlign="right">
            {configuredField(SAVED_SEARCH_FIELD)}
          </SavedSearchColumn>
        </Grid.Row>
      </Grid>
    </Header>
    <Header content="Customize Search:" />
    <VariantSearchFormPanels panels={PANEL_MAP[datasetTypes][hasHgmdPermission][displayAnnotationSecondary]} />
  </div>
))

VariantSearchFormContent.propTypes = {
  hasHgmdPermission: PropTypes.bool,
  displayAnnotationSecondary: PropTypes.bool,
  datasetTypes: PropTypes.string,
}

const mapStateToProps = state => ({
  hasHgmdPermission: getHasHgmdPermission(state),
  displayAnnotationSecondary: getAnnotationSecondary(state),
  datasetTypes: getDatasetTypes(state),
})

export default connect(mapStateToProps)(VariantSearchFormContent)
