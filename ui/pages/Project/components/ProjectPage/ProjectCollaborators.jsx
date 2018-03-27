import React from 'react'
import PropTypes from 'prop-types'
import orderBy from 'lodash/orderBy'

import { Table, Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'
import ShowIfEditPermissions from 'shared/components/ShowIfEditPermissions'
import { getProject } from 'redux/rootReducer'
import SectionHeader from 'shared/components/SectionHeader'


const ProjectCollaborators = props => (
  [
    <SectionHeader>Collaborators</SectionHeader>,
    <Table className="noBorder">
      <Table.Body className="noBorder">
        {
          orderBy(props.project.collaborators, [c => c.hasEditPermissions, c => c.email], ['desc', 'asc']).map((c, i) =>
            <Table.Row key={c.email} className="noBorder">
              <Table.Cell style={{ padding: '0px' }} className="noBorder">
                {c.displayName ? `${c.displayName} ▪ ` : null}
                {
                   c.email ?
                     <i><a href={`mailto:${c.email}`}>{c.email}</a></i> : null
                }

              </Table.Cell>
              <Table.Cell style={{ padding: '2px 10px', textAlign: 'center', verticalAlign: 'top' }} className="noBorder">
                <Popup
                  position="top center"
                  trigger={<b style={{ cursor: 'pointer' }}> {c.hasEditPermissions ? ' † ' : ' '}</b>}
                  content={"Has 'Manager' permissions"}
                  size="small"
                />
              </Table.Cell>
            </Table.Row>,
          )
        }
      </Table.Body>
    </Table>,
    <ShowIfEditPermissions>
      <a href={`/project/${props.project.deprecatedProjectId}/collaborators`}>
        Edit Collaborators
      </a>
    </ShowIfEditPermissions>,
  ]
)


ProjectCollaborators.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(ProjectCollaborators)
