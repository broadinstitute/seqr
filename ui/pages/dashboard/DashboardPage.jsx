import React from 'react'
import ReactDOM from 'react-dom'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import InitialSettingsProvider from '../../shared/components/setup/InitialSettingsProvider'
import BaseLayout from '../../shared/components/BaseLayout'
import ProjectsTable from './components/ProjectsTable'
import ReduxInit from '../../shared/components/setup/ReduxInit'

import rootReducer, { updateProjectInfo } from './reducers/rootReducer'

require('../../node_modules/semantic-ui/dist/semantic.css')
//require('../../third_party/semantic/dist/semantic.min.js')

class DashboardPage extends React.Component
{
  render = () => {
    return <BaseLayout {...this.props}>
      <span>
        <ProjectsTable {...this.props} />
      </span>
    </BaseLayout>
  }
}


const mapStateToProps = ({ user, projectsByGuid }) => {
  return {
    user,
    projectsByGuid,
  }
}

const mapDispatchToProps = dispatch => bindActionCreators({
  updateProjectInfo,
}, dispatch)


// wrap presentational components in a container so that redux state is passed in as props
const DashboardPageWrapper = connect(mapStateToProps, mapDispatchToProps)(DashboardPage)

ReactDOM.render(
  <InitialSettingsProvider>
    <ReduxInit storeName="Dashboard" rootReducer={rootReducer}>
      <DashboardPageWrapper />
    </ReduxInit>
  </InitialSettingsProvider>,
  document.getElementById('reactjs-root'),
)

