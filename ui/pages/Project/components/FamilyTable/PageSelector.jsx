import React from 'react'
import PropTypes from 'prop-types'
import { Pagination } from 'semantic-ui-react'
import { connect } from 'react-redux'

import QueryParamEditor from 'shared/components/QueryParamEditor'

import {
  getTotalPageCount,
} from '../../selectors'


const BasePageSelector = ({ currentQueryParam, totalPages, updateQueryParam }) =>
  <Pagination
    activePage={currentQueryParam || null}
    totalPages={totalPages}
    onPageChange={(e, d) => updateQueryParam(d.activePage)}
    size="mini"
  />

BasePageSelector.propTypes = {
  currentQueryParam: PropTypes.string,
  totalPages: PropTypes.number.isRequired,
  updateQueryParam: PropTypes.func.isRequired,
}

const mapStateToProps = state => ({
  totalPages: getTotalPageCount(state),
})

const PageSelector = connect(mapStateToProps)(BasePageSelector)

export default () =>
  <QueryParamEditor queryParam="page">
    <PageSelector />
  </QueryParamEditor>
