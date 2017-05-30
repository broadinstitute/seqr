import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Icon } from 'semantic-ui-react'

import { showTextEditorModal } from 'shared/components/modal/text-editor-modal/state'


const EditTextButton = props =>
  <a
    tabIndex="0"
    onClick={() => props.showTextEditorModal(
      props.modalSubmitUrl,
      props.modalTitle,
      props.initialText,
      props.allowRichText,
      props.modalId,
    )}
  >
    {
      props.label ?
        <div>
          <div style={{ cursor: 'pointer', display: 'inline-block', padding: '5px 10px 10px 12px' }}>{props.label}</div>
          <Icon link size="small" name="write" />
        </div>
        : <Icon link size="small" name="write" />
    }
  </a>

export { EditTextButton as EditTextButtonComponent }

EditTextButton.propTypes = {
  modalId: PropTypes.string,
  allowRichText: PropTypes.bool,
  initialText: PropTypes.string,
  modalTitle: PropTypes.string,
  modalSubmitUrl: PropTypes.string,
  label: PropTypes.string,

  showTextEditorModal: PropTypes.func.isRequired,
}

const mapDispatchToProps = {
  showTextEditorModal,
}

export default connect(null, mapDispatchToProps)(EditTextButton)
