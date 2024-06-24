import React from 'react'
import PropTypes from 'prop-types'

import { ButtonLink } from '../StyledComponents'
import FormWrapper from '../form/FormWrapper'
import Modal from '../modal/Modal'

const UpdateButton = React.memo(({
  onSubmit, initialValues, formFields, modalTitle, modalId, buttonText, editIconName, size, modalSize, showErrorPanel,
  disabled, confirmDialog, submitButtonText, buttonFloated, trigger, formContainer = <div />, modalPopup,
  decorators, formMetaId, submitOnChange,
}) => (
  <Modal
    title={modalTitle}
    modalName={modalId}
    size={modalSize}
    popup={modalPopup}
    trigger={trigger || (
      <ButtonLink
        content={buttonText}
        icon={editIconName || 'write'}
        labelPosition={buttonText && 'right'}
        size={size || 'small'}
        disabled={disabled}
        floated={buttonFloated}
      />
    )}
  >
    {React.cloneElement(formContainer, {
      children: (
        <FormWrapper
          onSubmit={onSubmit}
          modalName={modalId}
          initialValues={initialValues}
          fields={formFields}
          showErrorPanel={showErrorPanel}
          confirmDialog={confirmDialog}
          submitButtonText={submitButtonText}
          decorators={decorators}
          formMetaId={formMetaId}
          submitOnChange={submitOnChange}
          confirmCloseIfNotSaved
        />
      ),
    })}
  </Modal>
))

UpdateButton.propTypes = {
  formFields: PropTypes.arrayOf(PropTypes.object),
  onSubmit: PropTypes.func,
  modalTitle: PropTypes.string,
  modalId: PropTypes.string.isRequired,
  modalPopup: PropTypes.object,
  initialValues: PropTypes.object,
  buttonText: PropTypes.string,
  buttonFloated: PropTypes.string,
  submitButtonText: PropTypes.string,
  editIconName: PropTypes.string,
  formContainer: PropTypes.node,
  showErrorPanel: PropTypes.bool,
  disabled: PropTypes.bool,
  size: PropTypes.string,
  modalSize: PropTypes.string,
  confirmDialog: PropTypes.string,
  formMetaId: PropTypes.string,
  trigger: PropTypes.node,
  decorators: PropTypes.arrayOf(PropTypes.func),
  submitOnChange: PropTypes.bool,
}

export default UpdateButton
