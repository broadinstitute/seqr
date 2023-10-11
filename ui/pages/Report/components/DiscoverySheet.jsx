import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import AwesomeBar from 'shared/components/page/AwesomeBar'
import DataTable from 'shared/components/table/DataTable'
import DataLoader from 'shared/components/DataLoader'
import { InlineHeader, ActiveDisabledNavLink } from 'shared/components/StyledComponents'
import { DISCOVERY_SHEET_COLUMNS, CMG_PROJECT_PATH } from '../constants'
import { loadDiscoverySheet } from '../reducers'
import { getDiscoverySheetLoading, getDiscoverySheetLoadingError, getDiscoverySheetRows } from '../selectors'

const SEARCH_CATEGORIES = ['projects']

const LOADING_PROPS = { inline: true }

const getResultHref = result => `/report/discovery_sheet/${result.key}`

const DiscoverySheet = React.memo(({ match, data, loading, load, loadingError }) => (
  <DataLoader contentId={match.params.projectGuid} load={load} reloadOnIdUpdate content loading={false}>
    <InlineHeader size="medium" content="Project:" />
    <AwesomeBar
      categories={SEARCH_CATEGORIES}
      placeholder="Enter project name"
      inputwidth="350px"
      getResultHref={getResultHref}
    />
    <span>
      &nbsp; or &nbsp;
      <ActiveDisabledNavLink to={`/report/discovery_sheet/${CMG_PROJECT_PATH}`}>view all CMG projects</ActiveDisabledNavLink>
    </span>
    <DataTable
      striped
      collapsing
      horizontalScroll
      downloadFileName={`discovery_sheet_${match.params.projectGuid}`}
      idField="row_id"
      defaultSortColumn="family_id"
      emptyContent={loadingError || (match.params.projectGuid ? '0 cases found' : 'Select a project to view data')}
      loading={loading}
      data={data}
      columns={DISCOVERY_SHEET_COLUMNS}
      loadingProps={LOADING_PROPS}
    />
  </DataLoader>
))

DiscoverySheet.propTypes = {
  match: PropTypes.object,
  data: PropTypes.arrayOf(PropTypes.object),
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
