import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Icon } from 'semantic-ui-react'

import { showRichTextEditorModal } from 'shared/components/modal/text-editor-modal/state'


const EditTextButton = props =>
  <a
    role="button"
    tabIndex="0"
    onClick={() => props.showRichTextEditorModal(
      props.modalSubmitUrl,
      props.modalTitle,
      props.initialText,
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
  initialText: PropTypes.string,
  modalTitle: PropTypes.string,
  modalSubmitUrl: PropTypes.string,
  label: PropTypes.string,

  showRichTextEditorModal: PropTypes.func.isRequired,
}

const mapDispatchToProps = {
  showRichTextEditorModal,
}

export default connect(null, mapDispatchToProps)(EditTextButton)
