import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getLocusListIsLoading } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import VariantSearchFormContainer from 'shared/components/panel/search/VariantSearchFormContainer'
import { SaveSearchButton } from './SavedSearch'
import VariantSearchFormContent from './VariantSearchFormContent'
import { SEARCH_FORM_NAME } from '../constants'
import { getIntitialSearch, getMultiProjectSearchContextIsLoading } from '../selectors'
import { loadProjectFamiliesContext } from '../reducers'


const VariantSearchForm = React.memo(({ match, history, load, initialSearch, loading, contentLoading }) =>
  <DataLoader
    contentId={match.params}
    loading={loading}
    load={load}
    content={initialSearch}
    hideError
  >
    <VariantSearchFormContainer
      history={history}
      initialValues={initialSearch}
      form={SEARCH_FORM_NAME}
      loading={contentLoading}
    >
      <VariantSearchFormContent />
    </VariantSearchFormContainer>
    <SaveSearchButton />
  </DataLoader>,
)

VariantSearchForm.propTypes = {
  match: PropTypes.object,
  history: PropTypes.object,
  initialSearch: PropTypes.object,
  load: PropTypes.func,
  loading: PropTypes.bool,
  contentLoading: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  initialSearch: getIntitialSearch(state, ownProps),
  contentLoading: getLocusListIsLoading(state),
  loading: getMultiProjectSearchContextIsLoading(state),
})

const mapDispatchToProps = {
  load: loadProjectFamiliesContext,
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearchForm)
