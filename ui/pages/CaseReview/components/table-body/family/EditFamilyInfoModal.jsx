import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import {
  getEditFamilyInfoModalIsVisible,
  getEditFamilyInfoModalTitle,
  getEditFamilyInfoModaInitialText,
  getEditFamilyInfoModalSubmitUrl,
  updateFamiliesByGuid,
  hideEditFamilyInfoModal,
} from '../../../reducers/rootReducer'

import RichTextEditorModal from '../../../../../shared/components/RichTextEditorModal'


const EditFamilyInfoModal = props => (
  props.isVisible ?
    <RichTextEditorModal
      title={props.title}
      initialText={props.initialText}
      formSubmitUrl={props.formSubmitUrl}
      onClose={props.hideEditFamilyInfoModal}
      onSave={(responseJson) => { props.updateFamiliesByGuid(responseJson) }}
    /> :
    null
)

export { EditFamilyInfoModal as EditFamilyInfoModalComponent }

EditFamilyInfoModal.propTypes = {
  isVisible: React.PropTypes.bool.isRequired,
  title: React.PropTypes.string,
  initialText: React.PropTypes.string,
  formSubmitUrl: React.PropTypes.string,
  hideEditFamilyInfoModal: React.PropTypes.func.isRequired,
  updateFamiliesByGuid: React.PropTypes.func.isRequired,
}

const mapStateToProps = state => ({
  isVisible: getEditFamilyInfoModalIsVisible(state),
  title: getEditFamilyInfoModalTitle(state),
  initialText: getEditFamilyInfoModaInitialText(state),
  formSubmitUrl: getEditFamilyInfoModalSubmitUrl(state),
})

const mapDispatchToProps = dispatch => bindActionCreators({ hideEditFamilyInfoModal, updateFamiliesByGuid }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(EditFamilyInfoModal)
