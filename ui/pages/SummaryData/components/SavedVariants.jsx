import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch, NavLink } from 'react-router-dom'

import { Form, Button } from 'semantic-ui-react'

import { getGenesById } from 'redux/selectors'
import {
  REVIEW_TAG_NAME,
  KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME,
  VARIANT_SORT_FIELD,
  VARIANT_PER_PAGE_FIELD,
  VARIANT_TAGGED_DATE_FIELD,
  VARIANT_HIDE_EXCLUDED_FIELD,
  SHOW_ALL,
  DISCOVERY_CATEGORY_NAME,
} from 'shared/utils/constants'
import { StyledForm } from 'shared/components/form/FormHelpers'
import AwesomeBar from 'shared/components/page/AwesomeBar'
import SavedVariants from 'shared/components/panel/variants/SavedVariants'
import { HorizontalSpacer } from 'shared/components/Spacers'

import { loadSavedVariants, updateAllProjectSavedVariantTable } from '../reducers'

const GENE_SEARCH_CATEGORIES = ['genes']

const FILTER_FIELDS = [
  VARIANT_TAGGED_DATE_FIELD,
  VARIANT_SORT_FIELD,
  VARIANT_PER_PAGE_FIELD,
  VARIANT_HIDE_EXCLUDED_FIELD,
]

const TAG_OPTIONS = [
  DISCOVERY_CATEGORY_NAME,
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
  'Send for validation',
  'Validated',
  'Validation did not confirm',
  'Confident AR one hit',
  'Analyst high priority',
  'AIP',
  'seqr MME (old)',
  'Submit to Clinvar',
  'Share with KOMP',
].map(name => ({
  value: name,
  text: name,
  key: name,
  label: { empty: true, circular: true, style: { backgroundColor: 'white' } },
}))

const PAGE_URL = '/summary_data/saved_variants'

const getUpdateTagUrl =
  (selectedTag, match) => `${PAGE_URL}/${(selectedTag || []).join(';') || SHOW_ALL}${match.params.gene ? `/${match.params.gene}` : ''}`

const getGeneHref = tag => selectedGene => `${PAGE_URL}/${tag || SHOW_ALL}/${selectedGene.key}`

const BaseSavedVariants = React.memo(({ loadVariants, geneDetail, ...props }) => {
  const { params } = props.match
  const { tag, gene } = params

  return (
    <SavedVariants
      tagOptions={TAG_OPTIONS}
      filters={FILTER_FIELDS}
      getUpdateTagUrl={getUpdateTagUrl}
      loadVariants={loadVariants}
      summaryFullWidth
      multiple
      selectedTag={tag && tag.split(';').filter(t => t !== SHOW_ALL)}
      additionalFilter={
        <StyledForm inline>
          <Form.Field
            control={AwesomeBar}
            categories={GENE_SEARCH_CATEGORIES}
            inputwidth="200px"
            label="Gene"
            placeholder="Search for a gene"
            getResultHref={getGeneHref(tag)}
            inline
          />
          {gene && <HorizontalSpacer width={10} />}
          {gene && (
            <Button
              as={NavLink}
              content={(geneDetail || {}).geneSymbol || gene}
              size="tiny"
              color="grey"
              icon="delete"
              compact
              to={(tag && tag !== SHOW_ALL) ? `${PAGE_URL}/${tag}` : PAGE_URL}
            />
          )}
          <HorizontalSpacer width={10} />
        </StyledForm>
      }
      {...props}
    />
  )
})

const mapStateToProps = (state, ownProps) => ({
  geneDetail: getGenesById(state)[ownProps.match.params.gene],
})

const mapDispatchToProps = (dispatch, ownProps) => ({
  updateTableField: field => (value) => {
    dispatch(updateAllProjectSavedVariantTable({ [field]: value }))
  },
  loadVariants: (newParams) => {
    const { params } = ownProps.match

    const isInitialLoad = params === newParams
    const hasUpdatedTagOrGene = params.tag !== newParams.tag || params.gene !== newParams.gene

    if (hasUpdatedTagOrGene) {
      dispatch(updateAllProjectSavedVariantTable({ page: 1 }))
    }
    if (isInitialLoad || hasUpdatedTagOrGene) {
      dispatch(loadSavedVariants(newParams))
    }
  },
})

BaseSavedVariants.propTypes = {
  match: PropTypes.object,
  history: PropTypes.object,
  geneDetail: PropTypes.object,
  updateTableField: PropTypes.func,
  loadVariants: PropTypes.func,
}

const ConnectedSavedVariants = connect(mapStateToProps, mapDispatchToProps)(BaseSavedVariants)

const RoutedSavedVariants =
  ({ match }) => <Switch><Route path={`${match.url}/:tag?/:gene?`} component={ConnectedSavedVariants} /></Switch>

RoutedSavedVariants.propTypes = {
  match: PropTypes.object,
}

export default RoutedSavedVariants
