import React from 'react'
import PropTypes from 'prop-types'

import { Icon, Popup } from 'semantic-ui-react'
import Modal from 'shared/components/modal/Modal'

const ShowPhenotipsModalButton = ({ individual, isViewOnly, modalId }) => (
  individual.phenotipsPatientId ? (
    <Modal
      modalName={`Phenotips-${individual.individualGuid}-${isViewOnly ? 'view' : 'edit'}-${modalId || ''}`}
      title={`PhenoTips: ${individual.displayName}`}
      size="large"
      trigger={
        <div style={{ display: 'inline-block' }}>
          <a role="button" tabIndex="0" style={{ cursor: 'pointer' }} >
            {
              isViewOnly ?
                <Icon name="file pdf outline" title="PhenoTips PDF" />
                : <Icon name="write" size="small" title="Edit in PhenoTips" />
            }
          </a>
        </div>
      }
    >
      <iframe
        frameBorder={0}
        width="100%"
        height="750px"
        src={`/api/project/${individual.projectGuid}/patient/${individual.phenotipsPatientId}/phenotips_${isViewOnly ? 'pdf' : 'edit'}`}
      />
    </Modal>
  ) : (
    <Popup
      trigger={<Icon name="file pdf outline" title="PhenoTips PDF" />}
      content={<div>PhenoTips data not available for this individual.</div>}
      size="small"
    />
  )
)

ShowPhenotipsModalButton.propTypes = {
  individual: PropTypes.object.isRequired,
  isViewOnly: PropTypes.bool.isRequired,
  modalId: PropTypes.string,
}

export default ShowPhenotipsModalButton

