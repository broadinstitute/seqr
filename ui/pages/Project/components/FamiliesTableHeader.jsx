import React from 'react'
import { Table } from 'semantic-ui-react'
import SortByColumn from './SortByColumn'
import {
  SORT_BY_PROJECT_NAME,
  SORT_BY_PROJECT_SAMPLES,
  SORT_BY_NUM_FAMILIES,
  SORT_BY_NUM_INDIVIDUALS,
  SORT_BY_DATE_CREATED,
} from '../constants'

class ProjectsTableHeader extends React.PureComponent {

  render() {
    return <Table.Header>
      <Table.Row style={{ backgroundColor: '#F3F3F3', padding: '5px 5px 5px 5px' }}>
        <Table.HeaderCell>
          <div className="text-column-header">
            Name
            <SortByColumn sortBy={SORT_BY_PROJECT_NAME} />
          </div>
        </Table.HeaderCell>
        <Table.HeaderCell collapsing>
          <div className="numeric-column-header">
            Families
            <SortByColumn sortBy={SORT_BY_NUM_FAMILIES} />
          </div>
        </Table.HeaderCell>
        <Table.HeaderCell collapsing>
          <div className="numeric-column-header">
            Individuals
            <SortByColumn sortBy={SORT_BY_NUM_INDIVIDUALS} />
          </div>
        </Table.HeaderCell>
        <Table.HeaderCell collapsing>
          <div className="numeric-column-header">
            Samples
            <SortByColumn sortBy={SORT_BY_PROJECT_SAMPLES} />
          </div>
        </Table.HeaderCell>
        <Table.HeaderCell collapsing>
          <div className="text-column-header">
            Created Date
            <SortByColumn sortBy={SORT_BY_DATE_CREATED} />
          </div>
        </Table.HeaderCell>
      </Table.Row>
    </Table.Header>
  }
}

export default ProjectsTableHeader
