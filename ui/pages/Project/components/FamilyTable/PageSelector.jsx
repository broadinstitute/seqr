import React from 'react'
import PropTypes from 'prop-types'
import { Pagination } from 'semantic-ui-react'
import { connect } from 'react-redux'

import {
  setCurrentPage,
  getProjectTablePage,
} from '../../reducers'

import {
  getTotalPageCount,
} from '../../utils/selectors'


const PageSelector = ({ activePage, totalPages, setPage }) =>
  <Pagination
    activePage={activePage}
    totalPages={totalPages}
    onPageChange={(e, d) => setPage(d.activePage)}
    size="mini"
  />

PageSelector.propTypes = {
  activePage: PropTypes.number.isRequired,
  totalPages: PropTypes.number.isRequired,
  setPage: PropTypes.func.isRequired,
}

const mapStateToProps = state => ({
  activePage: getProjectTablePage(state),
  totalPages: getTotalPageCount(state),
})

const mapDispatchToProps = {
  setPage: setCurrentPage,
}

export default connect(mapStateToProps, mapDispatchToProps)(PageSelector)
