import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { loadLocusLists } from 'redux/rootReducer'
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


const BaseLocusListItemsLoader = ({ locusListGuid, locusList, genesById, loading, load, children }) => {
  const itemMap = (locusList.items || []).reduce((acc, item) => {
    if (item.geneId) {
      const gene = genesById[item.geneId]
      return { ...acc, [gene.symbol]: gene }
    }
    return { ...acc, [`chr${item.chrom}:${item.start}-${item.end}`]: item }
  }, {})
  locusList.parsedItems = {
    display: Object.keys(itemMap).sort().join(', '),
    itemMap,
    items: Object.values(itemMap),
  }
  return (
    <DataLoader contentId={locusListGuid || locusList.locusListGuid} content={locusList.items} loading={loading} load={load}>
      {children}
    </DataLoader>
  )
}

BaseLocusListItemsLoader.propTypes = {
  locusList: PropTypes.object,
  load: PropTypes.func,
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
}

export const LocusListsLoader = connect(mapStateToProps, mapDispatchToProps)(BaseLocusListsLoader)
export const LocusListItemsLoader = connect(mapStateToProps, mapDispatchToProps)(BaseLocusListItemsLoader)
