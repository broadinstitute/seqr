import 'react-hot-loader/patch'
import React from 'react'
import DocumentTitle from 'react-document-title'
import { Divider } from 'semantic-ui-react'

import ProjectsTable from './components/ProjectsTable'

const Dashboard = () => {
  return (
    <div>
      <DocumentTitle title="seqr: home" />
      <div style={{ textAlign: 'center', fontSize: '16px', fontWeight: 400, fontStyle: 'italic' }}>
         Welcome to the new seqr dashboard. The deprecated previous version can be found <a href="/projects">here</a>.
      </div>
      <Divider />
      <ProjectsTable />
    </div>
  )
}

export default Dashboard
