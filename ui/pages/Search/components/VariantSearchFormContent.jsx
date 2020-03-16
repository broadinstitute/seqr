import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Header, List } from 'semantic-ui-react'

import { getUser, getAnnotationSecondary } from 'redux/selectors'
import { VerticalSpacer } from 'shared/components/Spacers'
import { ButtonLink, InlineHeader } from 'shared/components/StyledComponents'
import { configuredField } from 'shared/components/form/ReduxFormWrapper'
import { Select } from 'shared/components/form/Inputs'
import Modal from 'shared/components/modal/Modal'
import VariantSearchFormPanels, {
  STAFF_PATHOGENICITY_PANEL, PATHOGENICITY_PANEL, ANNOTATION_PANEL, FREQUENCY_PANEL, LOCATION_PANEL, QUALITY_PANEL,
} from 'shared/components/panel/search/VariantSearchFormPanels'
import { ALL_INHERITANCE_FILTER } from 'shared/utils//constants'
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

const ANNOTATION_PANEL_SECONDARY = {
  ...ANNOTATION_PANEL,
  headerProps: { ...ANNOTATION_PANEL.headerProps, title: 'Annotations (Second Hit)' },
  name: 'annotations_secondary',
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

const PANEL_DETAILS = [
  INHERITANCE_PANEL, PATHOGENICITY_PANEL, ANNOTATION_PANEL, FREQUENCY_PANEL, LOCATION_PANEL_WITH_GENE_LIST, QUALITY_PANEL,
]
const STAFF_PANEL_DETAILS = [
  INHERITANCE_PANEL, STAFF_PATHOGENICITY_PANEL, ANNOTATION_PANEL, FREQUENCY_PANEL, LOCATION_PANEL_WITH_GENE_LIST, QUALITY_PANEL,
]
const PANEL_DETAILS_WITH_ANNOTATION_PANEL_SECONDARY_DETAILS = [
  INHERITANCE_PANEL, PATHOGENICITY_PANEL, ANNOTATION_PANEL, ANNOTATION_PANEL_SECONDARY, FREQUENCY_PANEL, LOCATION_PANEL_WITH_GENE_LIST, QUALITY_PANEL,
]
const STAFF_PANEL_DETAILS_WITH_ANNOTATION_PANEL_SECONDARY_DETAILS = [
  INHERITANCE_PANEL, STAFF_PATHOGENICITY_PANEL, ANNOTATION_PANEL, ANNOTATION_PANEL_SECONDARY, FREQUENCY_PANEL, LOCATION_PANEL_WITH_GENE_LIST, QUALITY_PANEL,
]

const VariantSearchFormContent = React.memo(({ user, displayAnnotationSecondary }) => {
  let panels
  if (displayAnnotationSecondary) {
    panels = user.isStaff ? STAFF_PANEL_DETAILS_WITH_ANNOTATION_PANEL_SECONDARY_DETAILS : PANEL_DETAILS_WITH_ANNOTATION_PANEL_SECONDARY_DETAILS
  }
  else {
    panels = user.isStaff ? STAFF_PANEL_DETAILS : PANEL_DETAILS
  }

  return (
    <div>
      <ProjectFamiliesField />
      <VerticalSpacer height={10} />
      <InlineHeader content="Saved Search:" />
      {configuredField(SAVED_SEARCH_FIELD)}
      <VariantSearchFormPanels panels={panels} />
    </div>
  )
})

VariantSearchFormContent.propTypes = {
  user: PropTypes.object,
  displayAnnotationSecondary: PropTypes.bool,
}

const mapStateToProps = state => ({
  user: getUser(state),
  displayAnnotationSecondary: getAnnotationSecondary(state),
})

export default connect(mapStateToProps)(VariantSearchFormContent)
