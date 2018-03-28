import React from 'react'
import PropTypes from 'prop-types'
import { Tab } from 'semantic-ui-react'

import Modal from '../../modal/Modal'
import UploadCallsetForm from './UploadCallsetForm'
import AddBamPathsForm from './AddBamPathsForm'

const UploadDatsetPanel = props =>
  <Tab
    renderActiveOnly={false}
    panes={[
      {
        menuItem: 'Upload New Callset',
        pane: <Tab.Pane key={1}><UploadCallsetForm handleClose={props.handleClose} /></Tab.Pane>,
      },
      {
        menuItem: 'Add BAM/CRAM Paths',
        pane: <Tab.Pane key={2}><AddBamPathsForm handleClose={props.handleClose} /></Tab.Pane>,
      },
    ]}
  />

UploadDatsetPanel.propTypes = {
  handleClose: PropTypes.func,
}


export default () => (
  <Modal
    title="Datasets"
    size="small"
    trigger={
      <div style={{ display: 'inline-block' }}>
        <a role="button" tabIndex="0" style={{ cursor: 'pointer' }}>Edit Datasets</a>
      </div>
    }
  >
    <UploadDatsetPanel />
  </Modal>
)
