import React from 'react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import PropTypes from 'prop-types'
import { Header, Message, Icon } from 'semantic-ui-react'

import SortableTable from 'shared/components/table/SortableTable'
import DataLoader from 'shared/components/DataLoader'
import { InlineHeader } from 'shared/components/StyledComponents'
import { getElasticsearchStatusLoading, getElasticsearchStatusData } from '../selectors'
import { loadElasticsearchStatus } from '../reducers'

const DISK_STAT_COLUMNS = [
  { name: 'node', content: 'Node name' },
  { name: 'diskAvail', content: 'Disk available' },
  { name: 'diskUsed', content: 'Disk used' },
  { name: 'diskPercent', content: 'Disk percentage used' },
]

const INDEX_COLUMNS = [
  { name: 'index', content: 'Index' },
  {
    name: 'projects',
    content: 'Project(s)',
    format: row => (row.projects ? row.projects.map(project =>
      <div key={project.projectGuid}>
        <Link to={`/project/${project.projectGuid}/project_page`} target="_blank">{project.projectName}</Link>
      </div>,
    ) : ''),
  },
  {
    name: 'hasNestedGenotypes',
    content: 'Nested Schema?',
    textAlign: 'center',
    format: row => (
      row.hasNestedGenotypes ? <Icon name="check circle" color="green" /> : <Icon name="remove circle" color="red" />
    ),
  },
  { name: 'sampleType', content: 'Data Type' },
  { name: 'genomeVersion', content: 'Genome Version' },
  { name: 'creationDateString', content: 'Created Date', format: row => row.creationDateString.split('T')[0] },
  { name: 'docsCount', content: '# Records' },
  { name: 'storeSize', content: 'Size' },
  { name: 'sourceFilePath', content: 'File Path' },
]

const MONGO_COLUMNS = [
  {
    name: 'projectGuid',
    content: 'Project(s)',
    format: row => (
      <Link key={row.projectGuid} to={`/project/${row.projectGuid}/project_page`} target="_blank">{row.projectName}</Link>
    ),
  },
  {
    name: 'sourceFilePaths',
    content: 'Mongo File Path(s)',
    format: row => row.sourceFilePaths.map(path => <div key={path}>{path}</div>),
  },
]

const ElasticsearchStatus = ({ data, loading, load }) =>
  <DataLoader load={load} content={Object.keys(data).length} loading={loading}>
    <InlineHeader size="small" content="Elasticsearch Host:" /> {data.elasticsearchHost}

    <Header size="medium" content="Disk Status:" />
    <SortableTable
      striped
      collapsing
      singleLine
      idField="node"
      defaultSortColumn="node"
      data={data.diskStats}
      columns={DISK_STAT_COLUMNS}
    />

    <Header size="medium" content="Loaded Indices:" />
    {data.errors && data.errors.length && <Message error list={data.errors} />}
    <SortableTable
      striped
      collapsing
      horizontalScroll
      idField="index"
      defaultSortColumn="creationDateString"
      defaultSortDescending
      data={data.indices}
      columns={INDEX_COLUMNS}
    />

    <Header size="medium" content="Mongo Projects:" />
    <SortableTable
      striped
      collapsing
      singleLine
      idField="projectGuid"
      defaultSortColumn="projectName"
      data={data.mongoProjects}
      columns={MONGO_COLUMNS}
    />
  </DataLoader>

ElasticsearchStatus.propTypes = {
  data: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = state => ({
  data: getElasticsearchStatusData(state),
  loading: getElasticsearchStatusLoading(state),
})

const mapDispatchToProps = {
  load: loadElasticsearchStatus,
}

export default connect(mapStateToProps, mapDispatchToProps)(ElasticsearchStatus)
