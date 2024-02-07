import React from 'react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import PropTypes from 'prop-types'
import { Header, Grid, Message, Button } from 'semantic-ui-react'

import DispatchRequestButton from 'shared/components/buttons/DispatchRequestButton'
import DataTable from 'shared/components/table/DataTable'
import DataLoader from 'shared/components/DataLoader'
import { DATASET_TYPE_SNV_INDEL_CALLS } from 'shared/utils/constants'
import { getElasticsearchStatusLoading, getElasticsearchStatusData } from '../selectors'
import { loadElasticsearchStatus, deleteEsIndex } from '../reducers'

const DISK_STAT_COLUMNS = [
  { name: 'node', content: 'Node name' },
  { name: 'shards', content: 'Shards' },
  { name: 'diskAvail', content: 'Disk available' },
  { name: 'diskUsed', content: 'Disk used' },
  { name: 'diskPercent', content: 'Disk %' },
  { name: 'heapPercent', content: 'Heap %' },
]

const NODE_STAT_COLUMNS = [
  { name: 'name', content: 'Node name' },
  { name: 'heapPercent', content: 'Heap %' },
]

const INDEX_COLUMNS = [
  { name: 'index', content: 'Index' },
  {
    name: 'projects',
    content: 'Project(s)',
    format: row => ((row.projects && row.projects.length) ? row.projects.map(project => (
      <div key={project.projectGuid}>
        <Link to={`/project/${project.projectGuid}/project_page`} target="_blank">{project.projectName}</Link>
      </div>
    )) : <DeleteIndexButton index={row.index} />),
  },
  {
    name: 'datasetType',
    content: 'Caller Type',
    format: row => (!row.datasetType || row.datasetType === DATASET_TYPE_SNV_INDEL_CALLS ? 'SNV' : row.datasetType),
  },
  { name: 'sampleType', content: 'Data Type' },
  { name: 'genomeVersion', content: 'Genome Version' },
  { name: 'creationDateString', content: 'Created Date', format: row => row.creationDateString.split('T')[0] },
  { name: 'docsCount', content: '# Records' },
  { name: 'storeSize', content: 'Size' },
  { name: 'sourceFilePath', content: 'File Path' },
]

const BaseDeleteIndexButton = ({ onSubmit, index }) => (
  <DispatchRequestButton confirmDialog={`Are you sure you want to delete "${index}"`} onSubmit={onSubmit}>
    <Button negative size="small" compact content="Delete Index" />
  </DispatchRequestButton>
)

BaseDeleteIndexButton.propTypes = {
  index: PropTypes.string,
  onSubmit: PropTypes.func,
}

const mapDeleteIndexDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: () => dispatch(deleteEsIndex(ownProps.index)),
})

const DeleteIndexButton = connect(null, mapDeleteIndexDispatchToProps)(BaseDeleteIndexButton)

const ElasticsearchStatus = React.memo(({ data, loading, load }) => (
  <DataLoader load={load} content={Object.keys(data).length} loading={loading}>
    <Grid columns={2}>
      <Grid.Column>
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
      </Grid.Column>
      <Grid.Column>
        <Header size="medium" content="Node Status:" />
        <DataTable
          striped
          collapsing
          singleLine
          idField="name"
          defaultSortColumn="name"
          data={data.nodeStats}
          columns={NODE_STAT_COLUMNS}
        />
      </Grid.Column>
    </Grid>

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
  </DataLoader>
))

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
