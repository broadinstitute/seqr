import React from 'react'
import DocumentTitle from 'react-document-title'

import ProjectsTable from './components/ProjectsTable'

export default () =>
  <div>
    <DocumentTitle title="seqr: home" />
    <ProjectsTable />
  </div>
