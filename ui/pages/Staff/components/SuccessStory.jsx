import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'

import AwesomeBar from 'shared/components/page/AwesomeBar'
import SortableTable from 'shared/components/table/SortableTable'
import { HorizontalSpacer } from 'shared/components/Spacers'
import DataLoader from 'shared/components/DataLoader'
import { InlineHeader } from 'shared/components/StyledComponents'
import { SUCCESS_STORY_COLUMNS } from '../constants'
import { loadDiscoverySheet } from '../reducers'
import { getDiscoverySheetLoading, getDiscoverySheetLoadingError, getDiscoverySheetRows } from '../selectors'

const getDownloadFilename = projectGuid => `discovery_sheet_${projectGuid}`

// eslint-disable-next-line camelcase
const getFamilyFilterVal = ({ family_id }) => `${family_id}`

const LOADING_PROPS = { inline: true }

const SEARCH_CATEGORIES = ['projects']

const ACTIVE_LINK_STYLE = {
  cursor: 'notAllowed',
  color: 'grey',
}

const getResultHref = page => result => `/staff/${page}/${result.key}`

const DiscoverySheet = ({ match, data, loading, loadingError, load, filters }) =>
  <DataLoader contentId={match.params.projectGuid} load={load} reloadOnIdUpdate content loading={false}>
    <InlineHeader size="medium" content="Projects:" />
    <AwesomeBar
      categories={SEARCH_CATEGORIES}
      placeholder="Enter project name"
      inputwidth="350px"
      getResultHref={getResultHref('discovery_sheet')}
    />
    or <NavLink to="/staff/discovery_sheet/all" activeStyle={ACTIVE_LINK_STYLE}>view all CMG projects</NavLink>
    <HorizontalSpacer width={20} />
    {filters}
    <SortableTable
      striped
      collapsing
      horizontalScroll
      downloadFileName={getDownloadFilename(match.params.projectGuid, data)}
      idField="row_id"
      defaultSortColumn="family_id"
      emptyContent={loadingError || (match.params.projectGuid ? '0 cases found' : 'Select a project to view data')}
      loading={loading}
      data={data}
      columns={SUCCESS_STORY_COLUMNS}
      loadingProps={LOADING_PROPS}
      getRowFilterVal={getFamilyFilterVal}
    />
  </DataLoader>

DiscoverySheet.propTypes = {
  match: PropTypes.object,
  data: PropTypes.array,
  loading: PropTypes.bool,
  loadingError: PropTypes.string,
  load: PropTypes.func,
  filters: PropTypes.node,
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
