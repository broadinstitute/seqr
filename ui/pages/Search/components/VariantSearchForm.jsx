import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getLocusListIsLoading } from 'redux/selectors'
import VariantSearchFormContainer from 'shared/components/panel/search/VariantSearchFormContainer'
import { SaveSearchButton } from './SavedSearch'
import VariantSearchFormContent from './VariantSearchFormContent'
import { getIntitialSearch, getMultiProjectFamilies } from '../selectors'

const VariantSearchForm = React.memo(({ history, initialSearch, contentLoading, noEditProjects }) => (
  <div>
    <VariantSearchFormContainer
      history={history}
      initialValues={initialSearch}
      loading={contentLoading}
    >
      <VariantSearchFormContent noEditProjects={noEditProjects} />
      <SaveSearchButton />
    </VariantSearchFormContainer>
  </div>
))

VariantSearchForm.propTypes = {
  history: PropTypes.object,
  initialSearch: PropTypes.object,
  contentLoading: PropTypes.bool,
  noEditProjects: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  initialSearch: getIntitialSearch(state, ownProps),
  contentLoading: getLocusListIsLoading(state),
})

export default connect(mapStateToProps)(VariantSearchForm)

const mapNoEditProjectStateToProps = (state, ownProps) => ({
  noEditProjects: true,
  initialSearch: getMultiProjectFamilies(state, ownProps),
  contentLoading: getLocusListIsLoading(state),
})

export const NoEditProjectsVariantSearchForm = connect(mapNoEditProjectStateToProps)(VariantSearchForm)
