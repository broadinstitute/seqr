import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Icon, Table } from 'semantic-ui-react'

import { getUser } from 'redux/rootReducer'
import EditProjectModal from 'shared/components/modal/EditProjectModal'
import ButtonLink from 'shared/components/buttons/ButtonLink'

const FooterCell = styled(Table.HeaderCell)`
  padding-right: 45px !important;
  font-weight: 300 !important;
`

const ProjectTableFooter = props => (
  props.user.is_staff ?
    <Table.Footer>
      <Table.Row>
        <FooterCell colSpan={10}>
          <EditProjectModal
            trigger={<ButtonLink float="right"><Icon name="plus" />Create Project</ButtonLink>}
            title="Create Project"
          />
        </FooterCell>
      </Table.Row>
    </Table.Footer>
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

