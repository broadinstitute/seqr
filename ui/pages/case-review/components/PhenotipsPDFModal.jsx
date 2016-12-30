import React from 'react'

import Modal from '../../../shared/components/Modal'


const PhenotipsPDFModal = props =>
  <Modal title={`${props.individualId}: PhenoTips PDF`} onClose={props.hidePhenotipsPDFModal} size="large">
    <iframe
      frameBorder={0}
      width="100%"
      height="750px"
      src={`/api/phenotips/proxy/view/${props.phenotipsId}?project=${props.projectId}`}
    />
  </Modal>


PhenotipsPDFModal.propTypes = {
  projectId: React.PropTypes.string.isRequired,
  individualId: React.PropTypes.string.isRequired,
  phenotipsId: React.PropTypes.string.isRequired,
  hidePhenotipsPDFModal: React.PropTypes.func.isRequired,
}

export default PhenotipsPDFModal
