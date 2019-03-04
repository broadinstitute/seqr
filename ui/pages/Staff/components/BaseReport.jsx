import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { NavLink } from 'react-router-dom'

import AwesomeBar from 'shared/components/page/AwesomeBar'
import SortableTable from 'shared/components/table/SortableTable'
import DataLoader from 'shared/components/DataLoader'
import { InlineHeader } from 'shared/components/StyledComponents'

const SEARCH_CATEGORIES = ['projects']

const ACTIVE_LINK_STYLE = {
  cursor: 'notAllowed',
  color: 'grey',
}

const LOADING_PROPS = { inline: true }

const AwesomebarContainer = styled.div`
  display: inline-block;
`

const getResultHref = page => result => `/staff/${page}/${result.key}`

const BaseReport = ({ page, viewAllCategory, idField, defaultSortColumn, getDownloadFilename, match, data, columns, loading, load, loadingError }) =>
  <DataLoader contentId={match.params.projectGuid} load={load} reloadOnIdUpdate content loading={false}>
    <InlineHeader size="medium" content="Projects:" />
    <AwesomebarContainer>
      <AwesomeBar
        categories={SEARCH_CATEGORIES}
        placeholder="Enter project name"
        inputwidth="400px"
        getResultHref={getResultHref(page)}
      />
    </AwesomebarContainer>
    or <NavLink to={`/staff/${page}/all`} activeStyle={ACTIVE_LINK_STYLE}>view all {viewAllCategory} projects</NavLink>
    <SortableTable
      striped
      collapsing
      horizontalScroll
      downloadFileName={getDownloadFilename(match.params.projectGuid, data)}
      idField={idField}
      defaultSortColumn={defaultSortColumn}
      emptyContent={loadingError || (match.params.projectGuid ? '0 cases found' : 'Select a project to view data')}
      loading={loading}
      data={data}
      columns={columns}
      loadingProps={LOADING_PROPS}
    />
  </DataLoader>

BaseReport.propTypes = {
  page: PropTypes.string,
  viewAllCategory: PropTypes.string,
  idField: PropTypes.string,
  defaultSortColumn: PropTypes.string,
  getDownloadFilename: PropTypes.func,
  match: PropTypes.object,
  data: PropTypes.array,
  columns: PropTypes.array,
  loading: PropTypes.bool,
  loadingError: PropTypes.string,
  load: PropTypes.func,
}

export default BaseReport
