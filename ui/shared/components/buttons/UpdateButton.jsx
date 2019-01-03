import React from 'react'
import PropTypes from 'prop-types'

import { ButtonLink } from '../StyledComponents'
import ReduxFormWrapper from '../form/ReduxFormWrapper'
import Modal from '../modal/Modal'

const UpdateButton = ({ onSubmit, initialValues, formFields, modalTitle, modalId, buttonText, editIconName, size, showErrorPanel, disabled, formContainer = <div /> }) =>
  <Modal
    title={modalTitle}
    modalName={modalId}
    trigger={
      <ButtonLink
        content={buttonText}
        icon={editIconName || 'write'}
        labelPosition={buttonText && 'right'}
        size={size}
        disabled={disabled}
      />
    }
  >
    {React.cloneElement(formContainer, { children: (
      <ReduxFormWrapper
        onSubmit={onSubmit}
        form={modalId}
        initialValues={initialValues}
        fields={formFields}
        showErrorPanel={showErrorPanel}
        confirmCloseIfNotSaved
      />
    ) }) }
  </Modal>

UpdateButton.propTypes = {
  formFields: PropTypes.array,
  onSubmit: PropTypes.func,
  modalTitle: PropTypes.string,
  modalId: PropTypes.string.isRequired,
  initialValues: PropTypes.object,
  buttonText: PropTypes.string,
  editIconName: PropTypes.string,
  formContainer: PropTypes.node,
  showErrorPanel: PropTypes.bool,
  disabled: PropTypes.bool,
  size: PropTypes.string,
}

export default UpdateButton
