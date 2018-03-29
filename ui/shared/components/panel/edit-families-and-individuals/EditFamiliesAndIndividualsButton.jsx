import React from 'react'
import PropTypes from 'prop-types'
import { Tab } from 'semantic-ui-react'
import styled from 'styled-components'
import Modal from '../../modal/Modal'
// import EditIndividualsBulkForm from './EditIndividualsBulkForm'
// import EditIndividualsForm from './EditIndividualsForm'
import EditFamiliesForm from './EditFamiliesForm'

const TabPane = styled(Tab.Pane)`
  padding: 1em 0 !important;
`

const TabPanel = props =>
  <Tab
    renderActiveOnly={false}
    panes={[
      {
        menuItem: 'Edit Families',
        pane: <TabPane key={1}><EditFamiliesForm onClose={props.handleClose} /></TabPane>,
      },
      // {
      //   menuItem: 'Edit Individuals',
      //   pane: <TabPane key={2}><EditIndividualsForm onClose={props.handleClose} /></TabPane>,
      // },
      // {
      //   menuItem: 'Bulk Upload',
      //   pane: (
      //     <TabPane key={3}>
      //       <EditIndividualsBulkForm onClose={() => { props.handleClose(); window.location.reload() }} />
      //     </TabPane>), //TODO update state without refreshing
      // },
    ]}
  />

TabPanel.propTypes = {
  handleClose: PropTypes.func,
}

export default () => (
  <Modal
    title="Edit Families & Individuals"
    size="large"
    trigger={
      <div style={{ display: 'inline-block' }}>
        <a role="button" tabIndex="0" style={{ cursor: 'pointer' }}>
          Edit Families & Individuals
        </a>
      </div>
    }
  >
    <TabPanel />
  </Modal>

)

