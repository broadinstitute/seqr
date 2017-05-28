import React from 'react'
import PropTypes from 'prop-types'

import { Icon, Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { showPhenotipsModal } from './phenotips-modal/state'


const ShowPhenotipsPDFButton = props => (
  <div style={{ display: 'inline-block' }}>
    {
      props.individual.phenotipsPatientId ?
        <a tabIndex="0" onClick={() => props.showPhenotipsModal(props.project, props.individual)} style={{ cursor: 'pointer' }}>
          <Icon name="file pdf outline" title="PhenoTips PDF" />
        </a>
        : <Popup
          trigger={<Icon name="file pdf outline" title="PhenoTips PDF" />}
          content={<div>PhenoTips data not available for this individual.</div>}
          size="small"
        />
    }
  </div>
)

ShowPhenotipsPDFButton.propTypes = {
  project: PropTypes.object.isRequired,
  individual: PropTypes.object.isRequired,

  showPhenotipsModal: PropTypes.func.isRequired,
}

export { ShowPhenotipsPDFButton as ShowPhenotipsPDFButtonComponent }

const mapDispatchToProps = {
  showPhenotipsModal,
}

export default connect(null, mapDispatchToProps)(ShowPhenotipsPDFButton)

