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
            <Icon link size="small" name={props.iconName || 'write'} />
          </div>
          : <Icon link size="small" name={props.iconName || 'write'} />
      }
    </a>
  }
  >
    <ReduxFormWrapper
      onSubmit={props.onSubmit}
      form={props.modalId}
      initialValues={props.initialValues}
      fields={[{ name: props.fieldId, component: RichTextEditor }, ...(props.additionalEditFields || [])]}
      confirmCloseIfNotSaved
    />
  </Modal>

EditTextButton.propTypes = {
  modalId: PropTypes.string,
  initialValues: PropTypes.object,
  modalTitle: PropTypes.string,
  onSubmit: PropTypes.func,
  fieldId: PropTypes.string,
  label: PropTypes.string,
  iconName: PropTypes.string,
  additionalEditFields: PropTypes.array,
}

export default EditTextButton
