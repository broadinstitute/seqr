import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { loadLocusLists } from 'redux/rootReducer'
import { getLocusListsByGuid, getLocusListsIsLoading } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'


const LocusLists = ({ locusLists, loading, load }) =>
  <DataLoader content={locusLists} loading={loading} load={load}>
    <div>{JSON.stringify(locusLists)}</div>
  </DataLoader>

LocusLists.propTypes = {
  locusLists: PropTypes.object,
  loading: PropTypes.bool.isRequired,
  load: PropTypes.func.isRequired,
}

const mapDispatchToProps = {
  load: loadLocusLists,
}

const mapStateToProps = state => ({
  locusLists: getLocusListsByGuid(state),
  loading: getLocusListsIsLoading(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(LocusLists)
