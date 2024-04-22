import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'

import { getUser } from 'redux/selectors'
import { NoHoverFamilyLink } from 'shared/components/buttons/FamilyLink'
import AwesomeBar from 'shared/components/page/AwesomeBar'
import DataTable from 'shared/components/table/DataTable'
import { HorizontalSpacer } from 'shared/components/Spacers'
import StateDataLoader from 'shared/components/StateDataLoader'
import { InlineHeader, ActiveDisabledNavLink } from 'shared/components/StyledComponents'

const ALL_PAGE = { downloadName: 'all_projects', path: 'all' }
const ANALYST_VIEW_ALL_PAGES = [
  { name: 'GREGoR', downloadName: 'all_GREGoR_projects', path: 'gregor' },
  { name: 'Broad', ...ALL_PAGE },
]
const VIEW_ALL_PAGES = [{ name: 'my', ...ALL_PAGE }]

const SEARCH_CATEGORIES = ['projects']
const URL_BASE = 'summary_data'

const getResultHref = urlPath => result => `/${URL_BASE}/${urlPath}/${result.key}`

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
  { projectGuid, queryForm, data, urlPath, user, columns, getColumns, idField },
) => (
  <div>
    <InlineHeader size="medium" content="Project:" />
    <AwesomeBar
      categories={SEARCH_CATEGORIES}
      placeholder="Enter project name"
      inputwidth="350px"
      getResultHref={getResultHref(urlPath)}
    />
    {(user.isAnalyst ? ANALYST_VIEW_ALL_PAGES : VIEW_ALL_PAGES).map(({ name, path }) => (
      <span key={path}>
        &nbsp; or &nbsp;
        <ActiveDisabledNavLink to={`/${URL_BASE}/${urlPath}/${path}`}>{`view all ${name} projects`}</ActiveDisabledNavLink>
      </span>
    ))}
    <HorizontalSpacer width={20} />
    {queryForm}
    <DataTable
      striped
      collapsing
      horizontalScroll
      downloadFileName={`${ANALYST_VIEW_ALL_PAGES.find(({ path }) => path === projectGuid)?.downloadName || (data?.length && data[0][PROJECT_ID_FIELD].replace(/ /g, '_'))}_${new Date().toISOString().slice(0, 10)}_${urlPath.split('_')[0]}_metadata`}
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
  user: PropTypes.object,
  queryForm: PropTypes.node,
  columns: PropTypes.arrayOf(PropTypes.object),
  getColumns: PropTypes.func,
  urlPath: PropTypes.string,
  idField: PropTypes.string,
}

const parseResponse = ({ rows }) => ({ data: rows })

const LoadReportTable = ({ match, urlPath, ...props }) => (
  <StateDataLoader
    url={match.params.projectGuid ? `/api/${URL_BASE}/${urlPath}/${match.params.projectGuid}` : ''}
    urlPath={urlPath}
    parseResponse={parseResponse}
    childComponent={ReportTable}
    projectGuid={match.params.projectGuid}
    {...props}
  />
)

LoadReportTable.propTypes = {
  match: PropTypes.object,
  urlPath: PropTypes.string,
}

const mapStateToProps = (state, ownProps) => {
  const user = getUser(state)
  return {
    user,
    queryFields: (user.isAnalyst && ownProps.match.params.projectGuid !== ALL_PAGE.path) ?
      ownProps.allQueryFields : ownProps.queryFields,
  }
}

export default connect(mapStateToProps)(LoadReportTable)
