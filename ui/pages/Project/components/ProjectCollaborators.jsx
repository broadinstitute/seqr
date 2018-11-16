import React from 'react'
import PropTypes from 'prop-types'
import orderBy from 'lodash/orderBy'
import styled from 'styled-components'

import { Table, Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { NoBorderTable } from 'shared/components/StyledComponents'
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
  <NoBorderTable compact="very">
    <Table.Body>
      {
        orderBy(props.project.collaborators, [c => c.hasEditPermissions, c => c.email], ['desc', 'asc']).map((c, i) =>
          <Table.Row key={c.email}>
            <NameCell>
              {c.displayName ? `${c.displayName} ▪ ` : null}
              {
                 c.email ?
                   <i><a href={`mailto:${c.email}`}>{c.email}</a></i> : null
              }

            </NameCell>
            <ManagerCell>
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
  </NoBorderTable>
)


ProjectCollaborators.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(ProjectCollaborators)
