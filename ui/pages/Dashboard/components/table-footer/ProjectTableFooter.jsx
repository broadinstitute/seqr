import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Icon, Table } from 'semantic-ui-react'

import { getUser, showModal } from '../../reducers/rootReducer'
import {
  ADD_PROJECT_MODAL,
} from '../../constants'


const ProjectTableFooter = props => (
  props.user.is_staff ?
    <Table.Row style={{ backgroundColor: '#F3F3F3' }}>
      <Table.Cell colSpan={10} style={{ paddingRight: '45px' }}>
        <a role="button" tabIndex="0" onClick={() => props.showModal(ADD_PROJECT_MODAL)} style={{ float: 'right', cursor: 'pointer' }}>
          <Icon name="plus" />Create Project
        </a>
      </Table.Cell>
    </Table.Row>
    : null
)

export { ProjectTableFooter as ProjectTableFooterComponent }

ProjectTableFooter.propTypes = {
  user: PropTypes.object.isRequired,
  showModal: PropTypes.func.isRequired,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

const mapDispatchToProps = { showModal }

export default connect(mapStateToProps, mapDispatchToProps)(ProjectTableFooter)

