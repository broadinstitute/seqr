import React from 'react'
import { Table } from 'semantic-ui-react'
import SortByColumn from './SortByColumn'
import {
  SORT_BY_PROJECT_NAME,
  SORT_BY_DATE_CREATED,
  SORT_BY_DATE_LAST_ACCESSED,
  SORT_BY_PROJECT_SAMPLES,
  SORT_BY_NUM_FAMILIES,
  SORT_BY_NUM_INDIVIDUALS,
  SORT_BY_TAGS,
  SORT_BY_ANALYSIS,
} from '../constants'

class ProjectsTableHeader extends React.PureComponent {
  static propTypes = {
    user: React.PropTypes.object.isRequired,
  }

  render() {
    return <Table.Header>
      <Table.Row>
        <Table.HeaderCell collapsing />
        <Table.HeaderCell>
          <div className="text-column-header">
            Name
            <SortByColumn sortBy={SORT_BY_PROJECT_NAME} />
          </div>
        </Table.HeaderCell>
        <Table.HeaderCell collapsing>
          <div className="numeric-column-header">
            Created
            <SortByColumn sortBy={SORT_BY_DATE_CREATED} />
          </div>
        </Table.HeaderCell>
        {
          this.props.user.is_staff &&
          <Table.HeaderCell collapsing>
            <div className="numeric-column-header">
              Last Accessed
              <SortByColumn sortBy={SORT_BY_DATE_LAST_ACCESSED} />
            </div>
          </Table.HeaderCell>
        }
        <Table.HeaderCell collapsing>
          <div className="numeric-column-header">
            Fam.
            <SortByColumn sortBy={SORT_BY_NUM_FAMILIES} />
          </div>
        </Table.HeaderCell>
        <Table.HeaderCell collapsing>
          <div className="numeric-column-header">
            Indiv.
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
          <div className="numeric-column-header">
            Tags
            <SortByColumn sortBy={SORT_BY_TAGS} />
          </div>
        </Table.HeaderCell>
        <Table.HeaderCell collapsing>
          <div className="numeric-column-header">
            Analysis
            <SortByColumn sortBy={SORT_BY_ANALYSIS} />
          </div>
        </Table.HeaderCell>
        <Table.HeaderCell collapsing />
      </Table.Row>
    </Table.Header>
  }
}

export default ProjectsTableHeader
