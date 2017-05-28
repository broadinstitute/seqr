import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import Modal from 'shared/components/modal/Modal'

import { getPhenotipsModalIsVisible, getPhenotipsModalProject, getPhenotipsModalIndividual, hidePhenotipsModal } from './state'


const PhenotipsModal = props => (
  props.isVisible ?
    <Modal
      title={`PhenoTips: ${props.individual.displayName || props.individual.individualId}`}
      onClose={props.hidePhenotipsModal}
      size="large"
    >
      {
        props.individual.phenotipsPatientId ?
          <iframe
            frameBorder={0}
            width="100%"
            height="750px"
            src={`/project/${props.project.projectGuid}/patient/${props.individual.phenotipsPatientId}/phenotips_view_patient_pdf`}
          /> :
          <div><b>Error:</b> {props.individual.displayName || props.individual.individualId} PhenoTips patient id is null.</div>
      }
    </Modal> :
    null
)

export { PhenotipsModal as PhenotipsModalComponent }


PhenotipsModal.propTypes = {
  isVisible: PropTypes.bool.isRequired,
  project: PropTypes.object,
  individual: PropTypes.object,
  hidePhenotipsModal: PropTypes.func.isRequired,
}


const mapStateToProps = state => ({
  isVisible: getPhenotipsModalIsVisible(state),
  project: getPhenotipsModalProject(state),
  individual: getPhenotipsModalIndividual(state),
})

const mapDispatchToProps = {
  hidePhenotipsModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(PhenotipsModal)
