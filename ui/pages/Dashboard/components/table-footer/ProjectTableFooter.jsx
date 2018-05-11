import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Icon, Table } from 'semantic-ui-react'

import { getUser } from 'redux/rootReducer'
import EditProjectModal from 'shared/components/modal/EditProjectModal'


const CreateProjectButton = styled.a.attrs({ role: 'button', tabIndex: '0' })`
  cursor: pointer;
  float: right;
  margin-right: 45px;
`
const FooterRow = styled(Table.Row)`
  background-color: #F3F3F3;
`

const ProjectTableFooter = props => (
  props.user.is_staff ?
    <FooterRow>
      <Table.Cell colSpan={10}>
        <EditProjectModal
          trigger={<CreateProjectButton><Icon name="plus" />Create Project</CreateProjectButton>}
          title="Create Project"
        />
      </Table.Cell>
    </FooterRow>
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

