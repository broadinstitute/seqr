import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import Modal from 'shared/components/modal/Modal'

import {
  getPhenotipsModalIsVisible,
  getPhenotipsModalProject,
  getPhenotipsModalIndividual,
  getPhenotipsModalIsViewOnly,
  hidePhenotipsModal,
} from './state'


const PhenotipsModal = (props) => {
  if (!props.isVisible) {
    return null
  }

  const url = props.isViewOnly ?
    `/project/${props.project.projectGuid}/patient/${props.individual.phenotipsPatientId}/phenotips_pdf` :
    `/project/${props.project.projectGuid}/patient/${props.individual.phenotipsPatientId}/phenotips_edit`

  return <Modal
    title={`PhenoTips: ${props.individual.displayName}`}
    onClose={() => {
      props.hidePhenotipsModal()
      // on second thought - users that want to see the latest changes can refresh the page manually
      /*
      if (!props.isViewOnly) {
        window.location.reload()  // refresh the current page after phenotips edits
      }
      */
    }}
    size="large"
  >
    {
      props.individual.phenotipsPatientId ?
        <iframe
          frameBorder={0}
          width="100%"
          height="750px"
          src={url}
        /> :
        <div><b>Error:</b> {props.individual.displayName} PhenoTips patient id is null.</div>
    }
  </Modal>
}

export { PhenotipsModal as PhenotipsModalComponent }


PhenotipsModal.propTypes = {
  isVisible: PropTypes.bool.isRequired,
  project: PropTypes.object,
  individual: PropTypes.object,
  isViewOnly: PropTypes.bool.isRequired,

  hidePhenotipsModal: PropTypes.func.isRequired,
}


const mapStateToProps = state => ({
  isVisible: getPhenotipsModalIsVisible(state),
  project: getPhenotipsModalProject(state),
  individual: getPhenotipsModalIndividual(state),
  isViewOnly: getPhenotipsModalIsViewOnly(state),
})

const mapDispatchToProps = {
  hidePhenotipsModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(PhenotipsModal)
