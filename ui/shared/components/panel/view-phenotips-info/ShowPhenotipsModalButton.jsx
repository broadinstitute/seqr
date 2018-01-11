import React from 'react'
import PropTypes from 'prop-types'

import { Icon, Popup } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { showPhenotipsModal } from './phenotips-modal/PhenotipsModal-redux'


const ShowPhenotipsModalButton = props => (
  <div style={{ display: 'inline-block' }}>
    {
      props.individual.phenotipsPatientId ?
        <a
          role="button"
          tabIndex="0"
          onClick={() => props.showPhenotipsModal(props.project, props.individual, props.isViewOnly)}
          style={{ cursor: 'pointer' }}
        >
          {
            props.isViewOnly ?
              <Icon name="file pdf outline" title="PhenoTips PDF" />
              : <Icon name="write" size="small" title="Edit in PhenoTips" />
          }
        </a>
        : <Popup
          trigger={<Icon name="file pdf outline" title="PhenoTips PDF" />}
          content={<div>PhenoTips data not available for this individual.</div>}
          size="small"
        />
    }
  </div>
)

ShowPhenotipsModalButton.propTypes = {
  project: PropTypes.object.isRequired,
  individual: PropTypes.object.isRequired,
  isViewOnly: PropTypes.bool.isRequired,

  showPhenotipsModal: PropTypes.func.isRequired,
}

export { ShowPhenotipsModalButton as ShowPhenotipsModalButtonComponent }

const mapDispatchToProps = {
  showPhenotipsModal,
}

export default connect(null, mapDispatchToProps)(ShowPhenotipsModalButton)

