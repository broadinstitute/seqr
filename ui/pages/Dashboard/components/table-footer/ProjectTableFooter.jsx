import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { Icon, Table } from 'semantic-ui-react'

import { getUser, getProjectCategoriesByGuid, showModal } from '../../reducers/rootReducer'
import {
  ADD_PROJECT_MODAL,
} from '../../constants'


const ProjectTableFooter = props => (
  props.user.is_staff &&
  <Table.Row style={{ backgroundColor: '#F3F3F3' }}>
    <Table.Cell colSpan={10} style={{ paddingRight: '45px' }}>
      <a tabIndex="0" onClick={() => props.showModal(ADD_PROJECT_MODAL)} style={{ float: 'right', cursor: 'pointer' }}>
        <Icon name="plus" />Create Project
      </a>
    </Table.Cell>
  </Table.Row>
)


ProjectTableFooter.propTypes = {
  user: React.PropTypes.object.isRequired,
  showModal: React.PropTypes.func.isRequired,
}

const mapStateToProps = state => ({
  user: getUser(state),
  projectCategoriesByGuid: getProjectCategoriesByGuid(state),
})

const mapDispatchToProps = dispatch => bindActionCreators({ showModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(ProjectTableFooter)

