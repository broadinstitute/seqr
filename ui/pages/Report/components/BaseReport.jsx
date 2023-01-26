import React from 'react'
import PropTypes from 'prop-types'
import { NavLink } from 'react-router-dom'

import AwesomeBar from 'shared/components/page/AwesomeBar'
import DataTable from 'shared/components/table/DataTable'
import { HorizontalSpacer } from 'shared/components/Spacers'
import DataLoader from 'shared/components/DataLoader'
import { InlineHeader } from 'shared/components/StyledComponents'

const SEARCH_CATEGORIES = ['projects']

const ACTIVE_LINK_STYLE = {
  cursor: 'notAllowed',
  color: 'grey',
}

const LOADING_PROPS = { inline: true }

const getResultHref = page => result => `/report/${page}/${result.key}`

const BaseReport = React.memo(({
  page, viewAllPages, idField, defaultSortColumn, getDownloadFilename, match, data, columns, loading, load,
  loadingError, filters, rowsPerPage,
}) => (
  <DataLoader contentId={match.params.projectGuid} load={load} reloadOnIdUpdate content loading={false}>
    <InlineHeader size="medium" content="Project:" />
    <AwesomeBar
      categories={SEARCH_CATEGORIES}
      placeholder="Enter project name"
      inputwidth="350px"
      getResultHref={getResultHref(page)}
    />
    {viewAllPages.map(({ name, path }) => (
      <span>
        &nbsp; or &nbsp;
        <NavLink to={`/report/${page}/${path}`} activeStyle={ACTIVE_LINK_STYLE}>{`view all ${name} projects`}</NavLink>
      </span>
    ))}
    <HorizontalSpacer width={20} />
    {filters}
    <DataTable
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
      rowsPerPage={rowsPerPage}
    />
  </DataLoader>
))

BaseReport.propTypes = {
  page: PropTypes.string,
  viewAllPages: PropTypes.arrayOf(PropTypes.object),
  idField: PropTypes.string,
  defaultSortColumn: PropTypes.string,
  getDownloadFilename: PropTypes.func,
  match: PropTypes.object,
  data: PropTypes.arrayOf(PropTypes.object),
  columns: PropTypes.arrayOf(PropTypes.object),
  loading: PropTypes.bool,
  loadingError: PropTypes.string,
  load: PropTypes.func,
  filters: PropTypes.node,
  rowsPerPage: PropTypes.number,
}

export default BaseReport
