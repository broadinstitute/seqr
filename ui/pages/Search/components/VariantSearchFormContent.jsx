import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { FormSpy } from 'react-final-form'
import styled from 'styled-components'
import { Header, List, Grid } from 'semantic-ui-react'

import { getElasticsearchEnabled } from 'redux/selectors'
import { ButtonLink } from 'shared/components/StyledComponents'
import { configuredField } from 'shared/components/form/FormHelpers'
import { Select } from 'shared/components/form/Inputs'
import Modal from 'shared/components/modal/Modal'
import VariantSearchFormPanels, {
  HGMD_PATHOGENICITY_PANEL, ANNOTATION_PANEL, FREQUENCY_PANEL, LOCATION_PANEL, QUALITY_PANEL, IN_SILICO_PANEL,
  annotationFieldLayout, inSilicoFieldLayout, JsonSelectPropsWithAll,
} from 'shared/components/panel/search/VariantSearchFormPanels'
import {
  HIGH_IMPACT_GROUPS_SPLICE, HIGH_IMPACT_GROUPS, MODERATE_IMPACT_GROUPS, CODING_IMPACT_GROUPS, ANY_PATHOGENICITY_FILTER,
  SV_GROUPS, SNP_FREQUENCIES, SNP_QUALITY_FILTER_FIELDS, PATHOGENICITY_FIELDS, PATHOGENICITY_FILTER_OPTIONS,
  MITO_FREQUENCIES, MITO_QUALITY_FILTER_FIELDS, SV_FREQUENCIES, SV_QUALITY_FILTER_FIELDS, CODING_IMPACT_GROUPS_SCREEN,
} from 'shared/components/panel/search/constants'
import {
  ALL_INHERITANCE_FILTER, DATASET_TYPE_VARIANT_CALLS, DATASET_TYPE_SV_CALLS, NO_SV_IN_SILICO_GROUPS, VEP_GROUP_SV_NEW,
  DATASET_TYPE_MITO_CALLS,
} from 'shared/utils/constants'
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

const ALL_DATASET_TYPE = `${DATASET_TYPE_MITO_CALLS},${DATASET_TYPE_SV_CALLS},${DATASET_TYPE_VARIANT_CALLS}`
const DATASET_TYPE_VARIANT_MITO = `${DATASET_TYPE_MITO_CALLS},${DATASET_TYPE_VARIANT_CALLS}`
const DATASET_TYPE_VARIANT_SV = `${DATASET_TYPE_SV_CALLS},${DATASET_TYPE_VARIANT_CALLS}`

const NO_HGMD_PANEL_PROPS = {
  headerProps: {
    ...HGMD_PATHOGENICITY_PANEL.headerProps,
    inputProps: JsonSelectPropsWithAll(PATHOGENICITY_FILTER_OPTIONS, ANY_PATHOGENICITY_FILTER),
  },
  fields: PATHOGENICITY_FIELDS,
}

const ANNOTATION_SECONDARY_NAME = 'annotations_secondary'
const SV_GROUPS_NO_NEW = SV_GROUPS.filter(name => name !== VEP_GROUP_SV_NEW)
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
  fieldLayout: annotationFieldLayout(
    [SV_GROUPS_NO_NEW, HIGH_IMPACT_GROUPS, MODERATE_IMPACT_GROUPS, CODING_IMPACT_GROUPS],
  ),
}

const PANELS = [
  INHERITANCE_PANEL,
  HGMD_PATHOGENICITY_PANEL,
  ANNOTATION_PANEL,
  ANNOTATION_SECONDARY_PANEL,
  IN_SILICO_PANEL,
  FREQUENCY_PANEL,
  LOCATION_PANEL_WITH_GENE_LIST,
  QUALITY_PANEL,
]

const DATASET_TYPE_PANEL_PROPS = {
  [DATASET_TYPE_VARIANT_CALLS]: {
    [ANNOTATION_PANEL.name]: {
      fieldLayout: annotationFieldLayout(
        [HIGH_IMPACT_GROUPS_SPLICE, MODERATE_IMPACT_GROUPS, CODING_IMPACT_GROUPS_SCREEN],
      ),
    },
    [ANNOTATION_SECONDARY_NAME]: {
      fieldLayout: annotationFieldLayout([HIGH_IMPACT_GROUPS, MODERATE_IMPACT_GROUPS, CODING_IMPACT_GROUPS]),
    },
    [IN_SILICO_PANEL.name]: {
      fieldLayout: inSilicoFieldLayout(NO_SV_IN_SILICO_GROUPS),
    },
    [FREQUENCY_PANEL.name]: {
      fields: SNP_FREQUENCIES,
    },
    [QUALITY_PANEL.name]: {
      fields: SNP_QUALITY_FILTER_FIELDS,
    },
  },
  [DATASET_TYPE_VARIANT_SV]: {
    [FREQUENCY_PANEL.name]: {
      fields: SNP_FREQUENCIES.concat(SV_FREQUENCIES),
    },
    [QUALITY_PANEL.name]: {
      fields: SNP_QUALITY_FILTER_FIELDS.concat(SV_QUALITY_FILTER_FIELDS),
    },
  },
}

DATASET_TYPE_PANEL_PROPS[DATASET_TYPE_VARIANT_MITO] = {
  ...DATASET_TYPE_PANEL_PROPS[DATASET_TYPE_VARIANT_CALLS],
  [FREQUENCY_PANEL.name]: {
    fields: SNP_FREQUENCIES.concat(MITO_FREQUENCIES),
  },
  [QUALITY_PANEL.name]: {
    fields: SNP_QUALITY_FILTER_FIELDS.concat(MITO_QUALITY_FILTER_FIELDS),
  },
}

const HAS_HGMD = true
const NO_HGMD = false
const HAS_ANN_SECONDARY = true
const NO_ANN_SECONDARY = false

const PANEL_MAP = [ALL_DATASET_TYPE, DATASET_TYPE_VARIANT_MITO, DATASET_TYPE_VARIANT_SV,
  DATASET_TYPE_VARIANT_CALLS].reduce((typeAcc, type) => {
  const typePanelProps = DATASET_TYPE_PANEL_PROPS[type] || {}
  const typePanels = PANELS.map(panel => ({ ...panel, ...(typePanelProps[panel.name] || {}) }))
  return {
    ...typeAcc,
    [type]: [HAS_HGMD, NO_HGMD].reduce((hgmdAcc, hasHgmdBool) => {
      const hgmdPanels = typePanels.map(panel => (
        (!hasHgmdBool && panel.name === HGMD_PATHOGENICITY_PANEL) ? { ...panel, ...NO_HGMD_PANEL_PROPS } : panel
      ))
      return {
        ...hgmdAcc,
        [hasHgmdBool]: [HAS_ANN_SECONDARY, NO_ANN_SECONDARY].reduce((acc, annSecondaryBool) => ({
          ...acc,
          [annSecondaryBool]: annSecondaryBool ? hgmdPanels :
            hgmdPanels.filter(({ name }) => name !== ANNOTATION_SECONDARY_NAME),
        }), {}),
      }
    }, {}),
  }
}, {})

const hasSecondaryAnnotation = inheritance => ALL_RECESSIVE_INHERITANCE_FILTERS.includes(inheritance?.mode)

const getPanels = (hasHgmdPermission, inheritance, datasetTypes) => (
  (PANEL_MAP[datasetTypes] || PANEL_MAP[ALL_DATASET_TYPE])[hasHgmdPermission][hasSecondaryAnnotation(inheritance)]
)

const VariantSearchFormContent = React.memo((
  { hasHgmdPermission, inheritance, datasetTypes, noEditProjects, esEnabled },
) => (
  <div>
    {!noEditProjects && <ProjectFamiliesField />}
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
    <VariantSearchFormPanels esEnabled={esEnabled} panels={getPanels(hasHgmdPermission, inheritance, datasetTypes)} />
  </div>
))

VariantSearchFormContent.propTypes = {
  hasHgmdPermission: PropTypes.bool,
  inheritance: PropTypes.object,
  datasetTypes: PropTypes.string,
  noEditProjects: PropTypes.bool,
  esEnabled: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  hasHgmdPermission: getHasHgmdPermission(state, ownProps),
  datasetTypes: getDatasetTypes(state, ownProps),
  esEnabled: getElasticsearchEnabled(state),
})

const ConnectedVariantSearchFormContent = connect(mapStateToProps)(VariantSearchFormContent)

const SUBSCRIPTION = { values: true }

export default props => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => (
      <ConnectedVariantSearchFormContent
        {...props}
        projectFamilies={values.projectFamilies}
        inheritance={values.search?.inheritance}
      />
    )}
  </FormSpy>
)
