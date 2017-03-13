import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import {
  getViewPhenotipsModalIsVisible,
  getViewPhenotipsModalProject,
  getViewPhenotipsModalIndividual,
  hideViewPhenotipsModal,
} from '../../../reducers/rootReducer'

import Modal from '../../../../../shared/components/Modal'


const ViewPhenotipsModal = props => (
  props.isVisible ?
    <Modal
      title={`${props.individual.displayName || props.individual.individualId}: PhenoTips PDF`}
      onClose={props.hideViewPhenotipsModal}
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


ViewPhenotipsModal.propTypes = {
  isVisible: React.PropTypes.bool.isRequired,
  project: React.PropTypes.object,
  individual: React.PropTypes.object,
  hideViewPhenotipsModal: React.PropTypes.func.isRequired,
}


const mapStateToProps = state => ({
  isVisible: getViewPhenotipsModalIsVisible(state),
  project: getViewPhenotipsModalProject(state),
  individual: getViewPhenotipsModalIndividual(state),
})

const mapDispatchToProps = dispatch => bindActionCreators({ hideViewPhenotipsModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(ViewPhenotipsModal)

