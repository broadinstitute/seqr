import React from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'

import { NoHoverFamilyLink } from 'shared/components/buttons/FamilyLink'
import AwesomeBar from 'shared/components/page/AwesomeBar'
import DataTable from 'shared/components/table/DataTable'
import { HorizontalSpacer } from 'shared/components/Spacers'
import StateDataLoader from 'shared/components/StateDataLoader'
import { InlineHeader, ActiveDisabledNavLink } from 'shared/components/StyledComponents'

const SEARCH_CATEGORIES = ['projects']

const getResultHref = urlBase => result => `/${urlBase}/${result.key}`

const PROJECT_ID_FIELD = 'internal_project_id'

const getTableColumns = columns => ([
  {
    name: PROJECT_ID_FIELD,
    content: 'project_id',
    format:
      row => <Link to={`/project/${row.projectGuid}/project_page`} target="_blank">{row[PROJECT_ID_FIELD]}</Link>,
    secondaryExportColumn: 'projectGuid',
  },
  {
    name: 'family_id',
    format: row => <NoHoverFamilyLink family={row} target="_blank" />,
    secondaryExportColumn: 'familyGuid',
  },
  ...columns,
].map(({ name, ...props }) => ({ name, content: name, ...props })))

const ReportTable = React.memo((
  { projectGuid, queryForm, data, urlBase, viewAllPages, columns, getColumns, idField, fileName },
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
      downloadFileName={`${viewAllPages.find(({ path }) => path === projectGuid)?.downloadName || (data?.length && data[0][PROJECT_ID_FIELD].replace(/ /g, '_'))}_${new Date().toISOString().slice(0, 10)}_${fileName}`}
      idField={idField}
      defaultSortColumn="family_id"
      emptyContent={projectGuid ? '0 cases found' : 'Select a project to view data'}
      data={data}
      columns={getTableColumns(columns || getColumns(data))}
      rowsPerPage={100}
    />
  </div>
))

ReportTable.propTypes = {
  data: PropTypes.arrayOf(PropTypes.object),
  projectGuid: PropTypes.string,
  viewAllPages: PropTypes.arrayOf(PropTypes.object),
  queryForm: PropTypes.node,
  columns: PropTypes.arrayOf(PropTypes.object),
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
