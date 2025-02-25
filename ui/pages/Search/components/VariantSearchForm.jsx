import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Segment } from 'semantic-ui-react'
import createDecorator from 'final-form-calculate'

import { navigateSavedHashedSearch } from 'redux/rootReducer'
import { getLocusListIsLoading } from 'redux/selectors'
import FormWrapper from 'shared/components/form/FormWrapper'
import { toUniqueCsvString } from 'shared/utils/stringUtils'
import { LOCUS_LIST_ITEMS_FIELD } from 'shared/utils/constants'

import SearchDisplayForm from './SearchDisplayForm'
import { SaveSearchButton } from './SavedSearch'
import VariantSearchFormContent from './VariantSearchFormContent'
import { LOCUS_FIELD_NAME, PANEL_APP_FIELD_NAME } from '../constants'
import { getIntitialSearch, getMultiProjectFamilies, getSearchedVariantsErrorMessage, getSearchedVariantsIsLoading } from '../selectors'

const DECORATORS = [
  createDecorator({
    field: `search.${LOCUS_FIELD_NAME}.${PANEL_APP_FIELD_NAME}`,
    updates: {
      [`search.${LOCUS_FIELD_NAME}.${LOCUS_LIST_ITEMS_FIELD.name}`]: locusValue => (
        locusValue && toUniqueCsvString(Object.values(locusValue))
      ),
    },
  }),
]

const VariantSearchForm = React.memo((
  { initialSearch, contentLoading, noEditProjects, match, onSubmit, variantsLoading, submissionError },
) => (
  <div>
    <FormWrapper
      onSubmit={onSubmit}
      initialValues={initialSearch}
      loading={contentLoading || variantsLoading}
      submissionError={submissionError}
      submitButtonText="Search"
      noModal
      decorators={DECORATORS}
    >
      <VariantSearchFormContent noEditProjects={noEditProjects} />
      <SaveSearchButton />
    </FormWrapper>
    {!match.params.searchHash && (
      <Segment basic floated="right"><SearchDisplayForm match={match} /></Segment>
    )}
  </div>
))

VariantSearchForm.propTypes = {
  match: PropTypes.object,
  initialSearch: PropTypes.object,
  contentLoading: PropTypes.bool,
  variantsLoading: PropTypes.bool,
  noEditProjects: PropTypes.bool,
  onSubmit: PropTypes.func,
  submissionError: PropTypes.string,
}

const mapDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: values => dispatch(navigateSavedHashedSearch(values, ownProps.history.push)),
})

const getSharedStateToProps = state => ({
  variantsLoading: getSearchedVariantsIsLoading(state),
  submissionError: getSearchedVariantsErrorMessage(state),
  contentLoading: getLocusListIsLoading(state),
})

const mapStateToProps = (state, ownProps) => ({
  initialSearch: getIntitialSearch(state, ownProps),
  ...getSharedStateToProps(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearchForm)

const mapNoEditProjectStateToProps = (state, ownProps) => ({
  noEditProjects: true,
  initialSearch: getMultiProjectFamilies(state, ownProps),
  ...getSharedStateToProps(state),
})

export const NoEditProjectsVariantSearchForm = connect(
  mapNoEditProjectStateToProps, mapDispatchToProps,
)(VariantSearchForm)
