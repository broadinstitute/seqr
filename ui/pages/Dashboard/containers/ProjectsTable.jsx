import React from 'react'
import { connect } from 'react-redux'
import { Table } from 'semantic-ui-react'

import ProjectsTableHeader from './ProjectsTableHeader'
import ProjectsTableRow from './ProjectsTableRow'

class ProjectsTable extends React.Component {

  static propTypes = {
    user: React.PropTypes.object.isRequired,
    projectsByGuid: React.PropTypes.object.isRequired,
  }

  render() {
    const {
      user,
      projectsByGuid,
    } = this.props

    return <Table celled style={{ width: '100%' }}>
      <Table.Body>
        <Table.Row style={{ backgroundColor: '#F3F3F3' /*'#D0D3DD'*/ }}>
          <Table.Cell>
            <ProjectsTableHeader />
          </Table.Cell>
        </Table.Row>
        {
          (() => {
            const keys = Object.keys(projectsByGuid)
            if (keys.length === 0) {
              return <Table.Row>
                <Table.Cell style={{ padding: '10px' }}>0 projects found</Table.Cell>
              </Table.Row>
            }

            return keys.map((projectGuid, i) => {
              const backgroundColor = (i % 2 === 0) ? 'white' : '#F3F3F3'
              return <Table.Row key={projectGuid} style={{ backgroundColor }}>

                <Table.Cell style={{ padding: '5px 0px 15px 15px' }}>
                  <ProjectsTableRow
                    user={user}
                    projectGuid={projectGuid}
                    projectsByGuid={projectsByGuid}
                  />
                </Table.Cell>
              </Table.Row>
            })
          })()
        }
      </Table.Body>
    </Table>
  }
}

const mapStateToProps = ({ user, projectsByGuid }) => ({ user, projectsByGuid })

export default connect(mapStateToProps)(ProjectsTable)
