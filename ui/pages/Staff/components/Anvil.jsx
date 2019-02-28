import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'

import AwesomeBar from 'shared/components/page/AwesomeBar'
import SortableTable from 'shared/components/table/SortableTable'
import DataLoader from 'shared/components/DataLoader'
import { InlineHeader } from 'shared/components/StyledComponents'

import { loadAnvil } from '../reducers'
import { getAnvilLoading, getAnvilLoadingError, getAnvilRows, getAnvilColumns } from '../selectors'

const SEARCH_CATEGORIES = ['projects']

const ACTIVE_LINK_STYLE = {
  cursor: 'notAllowed',
  color: 'grey',
}

const AwesomebarContainer = styled.div`
  display: inline-block;
`

const getResultHref = result => `/staff/anvil/${result.key}`

const getDownloadFilename = (projectGuid, data) => {
  const projectName = projectGuid && projectGuid !== 'all' && data.length && data[0]['Project ID'].replace(/ /g, '_')
  return `${projectName || 'All_AnVIL_Projects'}_${new Date().toISOString().slice(0, 10)}_Metadata`
}

const Anvil = ({ match, data, columns, loading, load, loadingError }) =>
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
    or <NavLink to="/staff/anvil/all" activeStyle={ACTIVE_LINK_STYLE}>view all AnVIL projects</NavLink>
    <SortableTable
      striped
      collapsing
      horizontalScroll
      downloadFileName={getDownloadFilename(match.params.projectGuid, data)}
      idField="individualGuid"
      defaultSortColumn="familyId"
      emptyContent={loadingError || (match.params.projectGuid ? '0 cases found' : 'Select a project to view data')}
      loading={loading}
      data={data}
      columns={columns}
    />
  </DataLoader>

Anvil.propTypes = {
  match: PropTypes.object,
  data: PropTypes.array,
  columns: PropTypes.array,
  loading: PropTypes.bool,
  loadingError: PropTypes.string,
  load: PropTypes.func,
}

const mapStateToProps = state => ({
  data: getAnvilRows(state),
  columns: getAnvilColumns(state),
  loading: getAnvilLoading(state),
  loadingError: getAnvilLoadingError(state),
})

const mapDispatchToProps = {
  load: loadAnvil,
}

export default connect(mapStateToProps, mapDispatchToProps)(Anvil)
