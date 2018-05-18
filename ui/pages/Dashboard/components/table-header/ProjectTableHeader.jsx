import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Table } from 'semantic-ui-react'
import styled from 'styled-components'

import SortableColumnHeader from './SortableColumnHeader'
import { getUser } from '../../../../redux/selectors'

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

const TableHeaderCell = styled(Table.HeaderCell)`
  padding: 12px 10px 12px 3px !important; 
  font-weight: 500 !important;
  text-align: ${props => props.textAlign}
`

class ProjectTableHeader extends React.PureComponent {
  static propTypes = {
    user: PropTypes.object.isRequired,
  }

  render() {
    return (
      <Table.Header>
        <Table.Row>
          <TableHeaderCell collapsing />
          <TableHeaderCell>
            <SortableColumnHeader columnLabel="Name" sortBy={SORT_BY_PROJECT_NAME} />
          </TableHeaderCell>
          <TableHeaderCell collapsing textAlign="right">
            <SortableColumnHeader columnLabel="Created" sortBy={SORT_BY_DATE_CREATED} />
          </TableHeaderCell>
          {
            this.props.user.is_staff &&
            <TableHeaderCell collapsing textAlign="right">
              <SortableColumnHeader columnLabel="Last Accessed" sortBy={SORT_BY_DATE_LAST_ACCESSED} />
            </TableHeaderCell>
          }
          <TableHeaderCell collapsing textAlign="right">
            <SortableColumnHeader columnLabel="Fam." sortBy={SORT_BY_NUM_FAMILIES} />
          </TableHeaderCell>
          <TableHeaderCell collapsing textAlign="right">
            <SortableColumnHeader columnLabel="Indiv." sortBy={SORT_BY_NUM_INDIVIDUALS} />
          </TableHeaderCell>
          <TableHeaderCell collapsing textAlign="right">
            <SortableColumnHeader columnLabel="Samples" sortBy={SORT_BY_PROJECT_SAMPLES} />
          </TableHeaderCell>
          <TableHeaderCell collapsing textAlign="right">
            <SortableColumnHeader columnLabel="Tags" sortBy={SORT_BY_TAGS} />
          </TableHeaderCell>
          <TableHeaderCell collapsing>
            <SortableColumnHeader columnLabel="Analysis" sortBy={SORT_BY_ANALYSIS} />
          </TableHeaderCell>
          <TableHeaderCell collapsing />
        </Table.Row>
      </Table.Header>)
  }
}

export { ProjectTableHeader as ProjectTableHeaderComponent }


const mapStateToProps = state => ({
  user: getUser(state),
})


export default connect(mapStateToProps)(ProjectTableHeader)
