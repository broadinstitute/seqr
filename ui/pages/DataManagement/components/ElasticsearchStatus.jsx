import React from 'react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import PropTypes from 'prop-types'
import { Header, Message } from 'semantic-ui-react'

import DataTable from 'shared/components/table/DataTable'
import DataLoader from 'shared/components/DataLoader'
import { InlineHeader } from 'shared/components/StyledComponents'
import { getElasticsearchStatusLoading, getElasticsearchStatusData } from '../selectors'
import { loadElasticsearchStatus } from '../reducers'

const DISK_STAT_COLUMNS = [
  { name: 'node', content: 'Node name' },
  { name: 'shards', content: 'Shards' },
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
  { name: 'datasetType', content: 'Caller Type', format: row => (row.datasetType === 'SV' ? 'SV' : 'SNV') },
  { name: 'sampleType', content: 'Data Type' },
  { name: 'genomeVersion', content: 'Genome Version' },
  { name: 'creationDateString', content: 'Created Date', format: row => row.creationDateString.split('T')[0] },
  { name: 'docsCount', content: '# Records' },
  { name: 'storeSize', content: 'Size' },
  { name: 'sourceFilePath', content: 'File Path' },
]

const ElasticsearchStatus = React.memo(({ data, loading, load }) =>
  <DataLoader load={load} content={Object.keys(data).length} loading={loading}>
    <InlineHeader size="small" content="Elasticsearch Host:" /> {data.elasticsearchHost}

    <Header size="medium" content="Disk Status:" />
    <DataTable
      striped
      collapsing
      singleLine
      idField="node"
      defaultSortColumn="node"
      data={data.diskStats}
      columns={DISK_STAT_COLUMNS}
    />

    <Header size="medium" content="Loaded Indices:" />
    {data.errors && data.errors.length > 0 && <Message error list={data.errors} />}
    <DataTable
      striped
      collapsing
      horizontalScroll
      idField="index"
      defaultSortColumn="creationDateString"
      defaultSortDescending
      data={data.indices}
      columns={INDEX_COLUMNS}
    />
  </DataLoader>,
)

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
