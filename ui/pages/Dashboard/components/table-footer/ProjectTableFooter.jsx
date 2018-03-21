import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Icon, Table } from 'semantic-ui-react'

import { getUser, saveProject } from 'redux/rootReducer'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import Modal from 'shared/components/modal/Modal'
import { ADD_PROJECT_MODAL } from '../../constants'


const CreateProjectButton = (
  <a role="button" tabIndex="0" style={{ float: 'right', cursor: 'pointer' }}>
    <Icon name="plus" />Create Project
  </a>
)

const ProjectTableFooter = props => (
  props.user.is_staff ?
    <Table.Row style={{ backgroundColor: '#F3F3F3' }}>
      <Table.Cell colSpan={10} style={{ paddingRight: '45px' }}>
        <Modal trigger={CreateProjectButton} title="Create Project" >
          <ReduxFormWrapper onSubmit={props.saveProject} {...ADD_PROJECT_MODAL} />
        </Modal>
      </Table.Cell>
    </Table.Row>
    : null
)

export { ProjectTableFooter as ProjectTableFooterComponent }

ProjectTableFooter.propTypes = {
  user: PropTypes.object.isRequired,
  saveProject: PropTypes.func,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

const mapDispatchToProps = {
  saveProject,
}

export default connect(mapStateToProps, mapDispatchToProps)(ProjectTableFooter)

