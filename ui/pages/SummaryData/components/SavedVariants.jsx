import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch } from 'react-router-dom'
import { Form, Label } from 'semantic-ui-react'

import { getGenesById } from 'redux/selectors'
import {
  REVIEW_TAG_NAME,
  KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME,
  VARIANT_SORT_FIELD,
  VARIANT_PER_PAGE_FIELD,
  VARIANT_TAGGED_DATE_FIELD,
  SHOW_ALL,
} from 'shared/utils/constants'
import { StyledForm } from 'shared/components/form/ReduxFormWrapper'
import AwesomeBar from 'shared/components/page/AwesomeBar'
import SavedVariants from 'shared/components/panel/variants/SavedVariants'
import { HorizontalSpacer } from 'shared/components/Spacers'

import { loadSavedVariants, updateAllProjectSavedVariantTable } from '../reducers'

const GENE_SEARCH_CATEGORIES = ['genes']

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
  'Analyst high priority',
  'MatchBox (MME)',
  'Submit to Clinvar',
  'Share with KOMP',
].map(name => ({
  value: name,
  text: name,
  key: name,
  label: { empty: true, circular: true, style: { backgroundColor: 'white' } },
}))

TAG_OPTIONS.push({
  value: SHOW_ALL,
  text: 'All',
  key: 'all',
  label: { empty: true, circular: true, style: { backgroundColor: 'white' } },
})

const BaseSavedVariants = React.memo(({ loadAllProjectSavedVariants, geneDetail, ...props }) => {
  const { params } = props.match
  const { tag, gene } = params

  const getUpdateTagUrl = selectedTag => `/summary_data/saved_variants/${selectedTag}${gene ? `/${gene}` : ''}`

  const getGeneHref = selectedGene => `/summary_data/saved_variants/${tag || SHOW_ALL}/${selectedGene.key}`

  const removeGene = () => props.history.push(`/summary_data/saved_variants/${tag || SHOW_ALL}`)

  const loadVariants = (newParams) => {
    const isInitialLoad = params === newParams
    const hasUpdatedTagOrGene = tag !== newParams.tag || gene !== newParams.gene

    if (hasUpdatedTagOrGene) {
      props.updateTable({ page: 1 })
    }
    if (isInitialLoad || hasUpdatedTagOrGene) {
      loadAllProjectSavedVariants(newParams)
    }
  }

  return (
    <SavedVariants
      tagOptions={TAG_OPTIONS}
      filters={FILTER_FIELDS}
      getUpdateTagUrl={getUpdateTagUrl}
      loadVariants={loadVariants}
      additionalFilter={
        <StyledForm inline>
          <Form.Field
            control={AwesomeBar}
            categories={GENE_SEARCH_CATEGORIES}
            inputwidth="200px"
            label="Gene"
            placeholder="Search for a gene"
            getResultHref={getGeneHref}
            inline
          />
          {gene && <HorizontalSpacer width={10} />}
          {gene && <Form.Field
            control={Label}
            content={(geneDetail || {}).geneSymbol || gene}
            inline
            color="grey"
            onRemove={removeGene}
          />}
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

const mapDispatchToProps = {
  updateTable: updateAllProjectSavedVariantTable,
  loadAllProjectSavedVariants: loadSavedVariants,
}

BaseSavedVariants.propTypes = {
  match: PropTypes.object,
  history: PropTypes.object,
  geneDetail: PropTypes.object,
  updateTable: PropTypes.func,
  loadAllProjectSavedVariants: PropTypes.func,
}

const ConnectedSavedVariants = connect(mapStateToProps, mapDispatchToProps)(BaseSavedVariants)

const RoutedSavedVariants = ({ match }) =>
  <Switch>
    <Route path={`${match.url}/:tag?/:gene?`} component={ConnectedSavedVariants} />
  </Switch>

RoutedSavedVariants.propTypes = {
  match: PropTypes.object,
}

export default RoutedSavedVariants
