import 'react-hot-loader/patch'
import React from 'react'
import DocumentTitle from 'react-document-title'
import { injectGlobal } from 'styled-components'
import { Divider } from 'semantic-ui-react'

import ProjectsTable from './components/ProjectsTable'
// import AddOrEditProjectModal from './components/table-body/AddOrEditProjectModal'
// import EditProjectCategoriesModal from './components/table-body/EditProjectCategoriesModal'

// TODO move this to releavant file
/* eslint-disable no-unused-expressions */
injectGlobal`
  .ui.table thead th {
    padding: 6px 3px;
    background-color: #F3F3F3;
    height: 10px;
  }
  
  .ui.form .field > label {
    text-align: left;
  }
  
  .ellipsis-menu {
    padding: 3px;
  }
  
  .ellipsis-menu:hover {
    padding: 3px;
    background-color: #fafafa;
    border-color: #ccc;
    border-radius: 3px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
  }
`

//<AddOrEditProjectModal />
//<EditProjectCategoriesModal />
const Dashboard = () => {
  return (
    <div>
      <DocumentTitle title="seqr: home" />
      <div style={{ textAlign: 'center', fontSize: '16px', fontWeight: 400, fontStyle: 'italic' }}>
         Welcome to the new seqr dashboard. The previous version can be found <a href="/projects">here</a>.
      </div>
      <Divider />
      <ProjectsTable />
    </div>
  )
}

export default Dashboard
