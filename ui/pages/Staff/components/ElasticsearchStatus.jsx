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
      <div key={project.guid}><Link to={`/project/${project.guid}/project_page`} target="_blank">{project.name}</Link></div>,
    ) : ''),
  },
  {
    name: 'hasNestedGenotypes',
    content: 'Nested Schema?',
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

const ElasticsearchStatus = ({ data, loading, load }) =>
  <DataLoader load={load} content={Object.keys(data).length} loading={loading}>
    <InlineHeader size="small" content="Elasticsearch Host:" /> {data.elasticsearchHost}

    <Header size="medium" content="Disk status:" />
    <SortableTable
      striped
      collapsing
      singleLine
      idField="node"
      defaultSortColumn="diskPercent"
      defaultSortDescending
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
