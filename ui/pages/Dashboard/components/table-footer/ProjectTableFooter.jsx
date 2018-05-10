import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Icon, Table } from 'semantic-ui-react'

import { getUser } from 'redux/selectors'
import EditProjectModal from 'shared/components/modal/EditProjectModal'


const CreateProjectButton = (
  <a role="button" tabIndex="0" style={{ float: 'right', cursor: 'pointer' }}>
    <Icon name="plus" />Create Project
  </a>
)

const ProjectTableFooter = props => (
  props.user.is_staff ?
    <Table.Row style={{ backgroundColor: '#F3F3F3' }}>
      <Table.Cell colSpan={10} style={{ paddingRight: '45px' }}>
        <EditProjectModal trigger={CreateProjectButton} title="Create Project" />
      </Table.Cell>
    </Table.Row>
    : null
)

export { ProjectTableFooter as ProjectTableFooterComponent }

ProjectTableFooter.propTypes = {
  user: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(ProjectTableFooter)

