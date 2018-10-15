import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { loadLocusLists, loadLocusListItems } from 'redux/rootReducer'
import { getLocusListIsLoading, getLocusListsByGuid, getGenesById } from 'redux/selectors'
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

export const parseLocusListItems = (locusList, genesById) => {
  const itemMap = (locusList.items || []).reduce((acc, item) => {
    if (item.geneId) {
      const gene = genesById[item.geneId]
      return { ...acc, [gene.geneSymbol]: gene }
    }
    return { ...acc, [`chr${item.chrom}:${item.start}-${item.end}`]: item }
  }, {})
  return {
    locusListGuid: locusList.locusListGuid,
    display: Object.keys(itemMap).sort().join(', '),
    itemMap,
    items: Object.values(itemMap),
  }
}


const BaseLocusListItemsLoader = ({ locusListGuid, locusList, genesById, loading, loadItems, children }) => {
  locusList.parsedItems = parseLocusListItems(locusList, genesById)
  return (
    <DataLoader contentId={locusListGuid || locusList.locusListGuid} content={locusList.items} loading={loading} load={loadItems}>
      {children}
    </DataLoader>
  )
}

BaseLocusListItemsLoader.propTypes = {
  locusList: PropTypes.object,
  loadItems: PropTypes.func,
  loading: PropTypes.bool,
  locusListGuid: PropTypes.string,
  genesById: PropTypes.object,
  children: PropTypes.node,
}

const mapStateToProps = state => ({
  loading: getLocusListIsLoading(state),
  genesById: getGenesById(state),
  locusListsByGuid: getLocusListsByGuid(state),
})

const mapDispatchToProps = {
  load: loadLocusLists,
  loadItems: loadLocusListItems,
}

export const LocusListsLoader = connect(mapStateToProps, mapDispatchToProps)(BaseLocusListsLoader)
export const LocusListItemsLoader = connect(mapStateToProps, mapDispatchToProps)(BaseLocusListItemsLoader)
