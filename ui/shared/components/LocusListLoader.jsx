import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { loadLocusLists } from 'redux/rootReducer'
import { getLocusListIsLoading, getLocusListsByGuid, getGenesById } from 'redux/selectors'
import DataLoader from './DataLoader'
import { compareObjects } from '../utils/sortUtils'

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


const BaseLocusListGeneLoader = ({ locusListGuid, locusList, genesById, loading, load, children }) => {
  locusList.genes = (locusList.geneIds || []).map(geneId => genesById[geneId]).sort(compareObjects('symbol'))
  return (
    <DataLoader contentId={locusListGuid || locusList.locusListGuid} content={locusList.geneIds} loading={loading} load={load}>
      {children}
    </DataLoader>
  )
}

BaseLocusListGeneLoader.propTypes = {
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
export const LocusListGeneLoader = connect(mapStateToProps, mapDispatchToProps)(BaseLocusListGeneLoader)
