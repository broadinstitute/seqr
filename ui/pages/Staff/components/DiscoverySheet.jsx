import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'

import AwesomeBar from 'shared/components/page/AwesomeBar'
import SortableTable from 'shared/components/table/SortableTable'
import DataLoader from 'shared/components/DataLoader'
import { InlineHeader } from 'shared/components/StyledComponents'

import { DISCOVERY_SHEET_COLUMNS } from '../constants'
import { loadDiscoverySheet } from '../reducers'
import { getDiscoverySheetLoading, getDiscoverySheetLoadingError, getDiscoverySheetRows } from '../selectors'

const SEARCH_CATEGORIES = ['projects']

const ACTIVE_LINK_STYLE = {
  cursor: 'notAllowed',
  color: 'grey',
}

const LOADING_PROPS = { inline: true }

const AwesomebarContainer = styled.div`
  display: inline-block;
`

const getResultHref = result => `/staff/discovery_sheet/${result.key}`

const DiscoverySheet = ({ match, data, loading, load, loadingError }) =>
  <DataLoader contentId={match.params.projectGuid} load={load} reloadOnIdUpdate content loading={false}>
    <InlineHeader size="medium" content="Projects:" />
    <AwesomebarContainer>
      <AwesomeBar
        categories={SEARCH_CATEGORIES}
        placeholder="Enter project name"
        inputwidth="400px"
        getResultHref={getResultHref}
      />
    </AwesomebarContainer>
    or <NavLink to="/staff/discovery_sheet/all" activeStyle={ACTIVE_LINK_STYLE}>view all CMG projects</NavLink>
    <SortableTable
      striped
      collapsing
      horizontalScroll
      downloadFileName={`discovery_sheet${match.params.projectGuid ? `_${match.params.projectGuid}` : ''}`}
      idField="family_guid"
      defaultSortColumn="family_id"
      emptyContent={loadingError || (match.params.projectGuid ? '0 cases found' : 'Select a project to view data')}
      loading={loading}
      data={data}
      columns={DISCOVERY_SHEET_COLUMNS}
      loadingProps={LOADING_PROPS}
    />
  </DataLoader>

DiscoverySheet.propTypes = {
  match: PropTypes.object,
  data: PropTypes.array,
  loading: PropTypes.bool,
  loadingError: PropTypes.string,
  load: PropTypes.func,
}

const mapStateToProps = state => ({
  data: getDiscoverySheetRows(state),
  loading: getDiscoverySheetLoading(state),
  loadingError: getDiscoverySheetLoadingError(state),
})

const mapDispatchToProps = {
  load: loadDiscoverySheet,
}

export default connect(mapStateToProps, mapDispatchToProps)(DiscoverySheet)
