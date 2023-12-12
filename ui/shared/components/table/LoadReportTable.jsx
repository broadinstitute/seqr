import React from 'react'
import PropTypes from 'prop-types'

import AwesomeBar from 'shared/components/page/AwesomeBar'
import DataTable from 'shared/components/table/DataTable'
import { HorizontalSpacer } from 'shared/components/Spacers'
import StateDataLoader from 'shared/components/StateDataLoader'
import { InlineHeader, ActiveDisabledNavLink } from 'shared/components/StyledComponents'

const SEARCH_CATEGORIES = ['projects']

const getResultHref = urlBase => result => `/${urlBase}/${result.key}`

const ReportTable = React.memo((
  { projectGuid, queryForm, data, urlBase, viewAllPages, getColumns, idField, fileName },
) => (
  <div>
    <InlineHeader size="medium" content="Project:" />
    <AwesomeBar
      categories={SEARCH_CATEGORIES}
      placeholder="Enter project name"
      inputwidth="350px"
      getResultHref={getResultHref(urlBase)}
    />
    {viewAllPages.map(({ name, path }) => (
      <span key={path}>
        &nbsp; or &nbsp;
        <ActiveDisabledNavLink to={`/${urlBase}/${path}`}>{`view all ${name} projects`}</ActiveDisabledNavLink>
      </span>
    ))}
    <HorizontalSpacer width={20} />
    {queryForm}
    <DataTable
      striped
      collapsing
      horizontalScroll
      downloadFileName={`${viewAllPages.find(({ path }) => path === projectGuid)?.downloadName || (data?.length && data[0].project_id.replace(/ /g, '_'))}_${new Date().toISOString().slice(0, 10)}_${fileName}`}
      idField={idField}
      defaultSortColumn="family_id"
      emptyContent={projectGuid ? '0 cases found' : 'Select a project to view data'}
      data={data}
      columns={getColumns(data)}
      rowsPerPage={100}
    />
  </div>
))

ReportTable.propTypes = {
  data: PropTypes.arrayOf(PropTypes.object),
  projectGuid: PropTypes.string,
  viewAllPages: PropTypes.arrayOf(PropTypes.object),
  queryForm: PropTypes.node,
  getColumns: PropTypes.func,
  urlBase: PropTypes.string,
  idField: PropTypes.string,
  fileName: PropTypes.string,
}

const parseResponse = ({ rows }) => ({ data: rows })

const LoadReportTable = ({ match, urlBase, ...props }) => (
  <StateDataLoader
    url={match.params.projectGuid ? `/api/${urlBase}/${match.params.projectGuid}` : ''}
    urlBase={urlBase}
    parseResponse={parseResponse}
    childComponent={ReportTable}
    projectGuid={match.params.projectGuid}
    {...props}
  />
)

LoadReportTable.propTypes = {
  match: PropTypes.object,
  urlBase: PropTypes.string,
}

export default LoadReportTable
