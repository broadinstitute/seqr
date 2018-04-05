import React from 'react'
import PropTypes from 'prop-types'
import { Icon } from 'semantic-ui-react'

import Modal from '../modal/Modal'
import ReduxFormWrapper from '../form/ReduxFormWrapper'
import RichTextEditor from '../form/RichTextEditor'

const EditTextButton = props =>
  <Modal title={props.modalTitle} modalName={props.modalId} trigger={
    <a role="button" tabIndex="0">
      {
        props.label ?
          <div>
            <div style={{ cursor: 'pointer', display: 'inline-block', padding: '5px 10px 10px 12px' }}>{props.label}</div>
            <Icon link size="small" name="write" />
          </div>
          : <Icon link size="small" name="write" />
      }
    </a>
  }
  >
    <ReduxFormWrapper
      onSubmit={props.onSubmit}
      form={props.modalId}
      initialValues={{ [props.fieldId]: props.initialText }}
      fields={[{ name: props.fieldId, component: RichTextEditor }]}
      confirmCloseIfNotSaved
    />
  </Modal>

EditTextButton.propTypes = {
  modalId: PropTypes.string,
  initialText: PropTypes.string,
  modalTitle: PropTypes.string,
  onSubmit: PropTypes.func,
  fieldId: PropTypes.string,
  label: PropTypes.string,
}

export default EditTextButton
