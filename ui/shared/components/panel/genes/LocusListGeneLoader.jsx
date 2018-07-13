import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { loadLocusLists } from 'redux/rootReducer'
import { getLocusListIsLoading, getGenesById } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { compareObjects } from 'shared/utils/sortUtils'


const LocusListGeneLoader = ({ locusListGuid, locusList, genesById, loading, load, children }) => {
  locusList.genes = (locusList.geneIds || []).map(geneId => genesById[geneId]).sort(compareObjects('symbol'))
  return (
    <DataLoader contentId={locusListGuid || locusList.locusListGuid} content={locusList.geneIds} loading={loading} load={load}>
      {children}
    </DataLoader>
  )
}

LocusListGeneLoader.propTypes = {
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
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    load: (locusListGuid) => {
      dispatch(loadLocusLists(locusListGuid, ownProps.projectGuid))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(LocusListGeneLoader)
