import 'react-hot-loader/patch'
import React from 'react'
import DocumentTitle from 'react-document-title'
import { injectGlobal } from 'styled-components'

import 'semantic-ui-css/semantic-custom.css'
import 'shared/global.css'

import ProjectsTable from './components/ProjectsTable'
import AddOrEditProjectModal from './components/table-body/AddOrEditProjectModal'
import EditProjectCategoriesModal from './components/table-body/EditProjectCategoriesModal'

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
const Dashboard = () => {
  return (
    <div>
      <DocumentTitle title="seqr: home" />
      <ProjectsTable />
      <AddOrEditProjectModal />
      <EditProjectCategoriesModal />
    </div>
  )
}

export default Dashboard
