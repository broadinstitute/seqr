import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch } from 'react-router-dom'

import { updateStaffSavedVariantTable } from 'redux/rootReducer'
import {
  REVIEW_TAG_NAME,
  KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME,
  VARIANT_SORT_FIELD,
  VARIANT_PER_PAGE_FIELD,
  VARIANT_TAGGED_DATE_FIELD,
} from 'shared/utils/constants'
import { SavedVariants } from 'shared/components/panel/variants/SavedVariants'

const FILTER_FIELDS = [
  VARIANT_TAGGED_DATE_FIELD,
  VARIANT_SORT_FIELD,
  VARIANT_PER_PAGE_FIELD,
]

const TAG_OPTIONS = [
  'Tier 1 - Novel gene and phenotype',
  'Tier 1 - Novel gene for known phenotype',
  'Tier 1 - Phenotype expansion',
  'Tier 1 - Phenotype not delineated',
  'Tier 1 - Novel mode of inheritance',
  'Tier 1 - Known gene, new phenotype',
  'Tier 2 - Novel gene and phenotype',
  'Tier 2 - Novel gene for known phenotype',
  'Tier 2 - Phenotype expansion',
  'Tier 2 - Phenotype not delineated',
  'Tier 2 - Known gene, new phenotype',
  KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME,
  REVIEW_TAG_NAME,
  'Send for Sanger validation',
  'Sanger validated',
  'Sanger did not confirm',
  'Confident AR one hit',
  'MatchBox (MME)',
  'Submit to Clinvar',
  'Share with KOMP',
].map(name => ({
  value: name,
  text: name,
  key: name,
  label: { empty: true, circular: true, style: { backgroundColor: 'white' } },
}))

const BaseStaffSavedVariants = props =>
  <SavedVariants
    tagOptions={TAG_OPTIONS}
    filters={FILTER_FIELDS}
    filterByGene
    {...props}
  />

const mapDispatchToProps = {
  updateTable: updateStaffSavedVariantTable,
}

const StaffSavedVariants = connect(null, mapDispatchToProps)(BaseStaffSavedVariants)

const RoutedSavedVariants = ({ match }) =>
  <Switch>
    <Route path={`${match.url}/:tag/gene/:gene`} component={StaffSavedVariants} />
    <Route path={`${match.url}/:tag?`} component={StaffSavedVariants} />
  </Switch>

RoutedSavedVariants.propTypes = {
  match: PropTypes.object,
}

export default RoutedSavedVariants
