import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { loadLocusLists, loadLocusListItems } from 'redux/rootReducer'
import { getLocusListIsLoading, getLocusListsByGuid, getParsedLocusList } from 'redux/selectors'
import DataLoader from './DataLoader'

const BaseLocusListsLoader = ({ locusListsByGuid, loading, load, children }) =>
  <DataLoader content={locusListsByGuid} loading={loading} load={load}>
    {children}
  </DataLoader>

BaseLocusListsLoader.propTypes = {
  load: PropTypes.func,
  loading: PropTypes.bool,
  locusListsByGuid: PropTypes.object,
  children: PropTypes.node,
}


const mapListsStateToProps = state => ({
  loading: getLocusListIsLoading(state),
  locusListsByGuid: getLocusListsByGuid(state),
})

const mapListsDispatchToProps = {
  load: loadLocusLists,
}

export const LocusListsLoader = connect(mapListsStateToProps, mapListsDispatchToProps)(BaseLocusListsLoader)

const BaseLocusListItemsLoader = ({ locusListGuid, locusList, loading, load, children, ...props }) =>
  <DataLoader contentId={locusListGuid} content={locusList.items} loading={loading} load={load} {...props}>
    {React.cloneElement(children, { locusList })}
  </DataLoader>

BaseLocusListItemsLoader.propTypes = {
  locusList: PropTypes.object,
  load: PropTypes.func,
  loading: PropTypes.bool,
  locusListGuid: PropTypes.string,
  children: PropTypes.node,
}

const mapItemsStateToProps = (state, ownProps) => ({
  loading: !ownProps.hideLoading && getLocusListIsLoading(state),
  locusList: getParsedLocusList(state, ownProps),
})

const mapItemsDispatchToProps = {
  load: loadLocusListItems,
}

export const LocusListItemsLoader = connect(mapItemsStateToProps, mapItemsDispatchToProps)(BaseLocusListItemsLoader)
