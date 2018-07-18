import React from 'react'
import PropTypes from 'prop-types'
import orderBy from 'lodash/orderBy'
import styled from 'styled-components'

import { Table, Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { getProject } from '../selectors'

const NameCell = styled(Table.Cell)`
  padding: 0;
`
const ManagerCell = styled(Table.Cell)`
  padding: 2px 10px;
  text-align: center;
  vertical-align: top;
`

const ProjectCollaborators = props => (
  <Table className="noBorder" compact="very">
    <Table.Body className="noBorder">
      {
        orderBy(props.project.collaborators, [c => c.hasEditPermissions, c => c.email], ['desc', 'asc']).map((c, i) =>
          <Table.Row key={c.email} className="noBorder">
            <NameCell className="noBorder">
              {c.displayName ? `${c.displayName} ▪ ` : null}
              {
                 c.email ?
                   <i><a href={`mailto:${c.email}`}>{c.email}</a></i> : null
              }

            </NameCell>
            <ManagerCell className="noBorder">
              <Popup
                position="top center"
                trigger={<b style={{ cursor: 'pointer' }}> {c.hasEditPermissions ? ' † ' : ' '}</b>}
                content={"Has 'Manager' permissions"}
                size="small"
              />
            </ManagerCell>
          </Table.Row>,
        )
      }
    </Table.Body>
  </Table>
)


ProjectCollaborators.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(ProjectCollaborators)
