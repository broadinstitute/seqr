import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Table } from 'semantic-ui-react'

import SortableColumnHeader from './SortableColumnHeader'
import { getUser } from '../../reducers/rootReducer'

import {
  SORT_BY_PROJECT_NAME,
  SORT_BY_DATE_CREATED,
  SORT_BY_DATE_LAST_ACCESSED,
  SORT_BY_PROJECT_SAMPLES,
  SORT_BY_NUM_FAMILIES,
  SORT_BY_NUM_INDIVIDUALS,
  SORT_BY_TAGS,
  SORT_BY_ANALYSIS,
} from '../../constants'


const textColumnHeader = {
  color: '#333333',
  fontWeight: 500,
  padding: '6px 0px 6px 6px',
}

const numericColumnHeader = {
  color: '#333333',
  textAlign: 'right',
  fontWeight: 500,
  padding: '6px 7px 6px 0px',
}


class ProjectTableHeader extends React.PureComponent {
  static propTypes = {
    user: PropTypes.object.isRequired,
  }

  render() {
    return <Table.Header>
      <Table.Row>
        <Table.HeaderCell collapsing />
        <Table.HeaderCell>
          <div style={textColumnHeader}><SortableColumnHeader columnLabel="Name" sortBy={SORT_BY_PROJECT_NAME} /></div>
        </Table.HeaderCell>
        <Table.HeaderCell collapsing>
          <div style={numericColumnHeader}><SortableColumnHeader columnLabel="Created" sortBy={SORT_BY_DATE_CREATED} /></div>
        </Table.HeaderCell>
        {
          this.props.user.is_staff &&
          <Table.HeaderCell collapsing>
            <div style={numericColumnHeader}><SortableColumnHeader style={numericColumnHeader} columnLabel="Last Accessed" sortBy={SORT_BY_DATE_LAST_ACCESSED} /></div>
          </Table.HeaderCell>
        }
        <Table.HeaderCell collapsing>
          <div style={numericColumnHeader}><SortableColumnHeader columnLabel="Fam." sortBy={SORT_BY_NUM_FAMILIES} /></div>
        </Table.HeaderCell>
        <Table.HeaderCell collapsing>
          <div style={numericColumnHeader}><SortableColumnHeader columnLabel="Indiv." sortBy={SORT_BY_NUM_INDIVIDUALS} /></div>
        </Table.HeaderCell>
        <Table.HeaderCell collapsing>
          <div style={numericColumnHeader}><SortableColumnHeader columnLabel="Samples" sortBy={SORT_BY_PROJECT_SAMPLES} /></div>
        </Table.HeaderCell>
        <Table.HeaderCell collapsing>
          <div style={numericColumnHeader}><SortableColumnHeader columnLabel="Tags" sortBy={SORT_BY_TAGS} /></div>
        </Table.HeaderCell>
        <Table.HeaderCell collapsing>
          <div style={textColumnHeader}><SortableColumnHeader columnLabel="Analysis" sortBy={SORT_BY_ANALYSIS} /></div>
        </Table.HeaderCell>
        <Table.HeaderCell collapsing />
      </Table.Row>
    </Table.Header>
  }
}

export { ProjectTableHeader as ProjectTableHeaderComponent }


const mapStateToProps = state => ({
  user: getUser(state),
})


export default connect(mapStateToProps)(ProjectTableHeader)
