import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import {
  getPhenotipsPDFModalIsVisible,
  getPhenotipsPDFModalProject,
  getPhenotipsPDFModalIndividual,
  hidePhenotipsPDFModal,
} from '../../../reducers/rootReducer'

import Modal from '../../../../../shared/components/Modal'


const PhenotipsPDFModal = props =>
  <Modal
    title={`${props.individual.displayName || props.individual.individualId}: PhenoTips PDF`}
    onClose={props.hidePhenotipsPDFModal}
    size="large"
  >
    <iframe
      frameBorder={0}
      width="100%"
      height="750px"
      src={`/project/${props.project.projectGuid}/patient/${props.individual.phenotipsPatientId}/phenotips_view_patient_pdf`}
    />
  </Modal>


PhenotipsPDFModal.propTypes = {
  project: React.PropTypes.object.isRequired,
  individual: React.PropTypes.object.isRequired,
  hidePhenotipsPDFModal: React.PropTypes.func.isRequired,
}


const mapStateToProps = state => ({
  isVisible: getPhenotipsPDFModalIsVisible(state),
  project: getPhenotipsPDFModalProject(state),
  indivdual: getPhenotipsPDFModalIndividual(state),
})

const mapDispatchToProps = dispatch => bindActionCreators({ hidePhenotipsPDFModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(PhenotipsPDFModal)

