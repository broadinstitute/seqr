import React from 'react'
import PropTypes from 'prop-types'
import UpdateButton from './UpdateButton'
import { BaseSemanticInput } from '../form/Inputs'

const CONTACT_URL_REGEX = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}(,\s*[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{1,4})*$/i

const NO_RECIPIENT_CONTACT_FIELDS = [
  { name: 'subject', label: 'Subject:' },
  { name: 'body', component: BaseSemanticInput, inputType: 'TextArea', rows: 12 },
]
const CONTACT_FIELDS = [
  {
    name: 'to',
    label: 'Send To:',
    validate: val => (CONTACT_URL_REGEX.test(val) ? undefined : 'Invalid Contact Email'),
  },
  ...NO_RECIPIENT_CONTACT_FIELDS,
]

const SendEmailButton = React.memo((
  { defaultEmail, onSubmit, modalId, idField, draftOnly, editRecipient, modalTitleDetail, ...props },
) => (defaultEmail ? (
  // when submitOnChange is true, no submit button is shown
  <UpdateButton
    submitOnChange={draftOnly}
    onSubmit={!draftOnly && onSubmit}
    initialValues={defaultEmail}
    formFields={editRecipient ? CONTACT_FIELDS : NO_RECIPIENT_CONTACT_FIELDS}
    modalTitle={`${draftOnly ? 'Draft' : 'Send'} Contact Email${modalTitleDetail ? modalTitleDetail(defaultEmail[idField]) : ''}`}
    modalId={`contactEmail-${modalId || defaultEmail[idField]}`}
    editIconName="mail"
    showErrorPanel
    submitButtonText="Send"
    buttonFloated="right"
    {...props}
  />
) : null))

SendEmailButton.propTypes = {
  defaultEmail: PropTypes.object.isRequired,
  onSubmit: PropTypes.func,
  modalId: PropTypes.string,
  idField: PropTypes.string,
  draftOnly: PropTypes.bool,
  editRecipient: PropTypes.bool,
  modalTitleDetail: PropTypes.string,
}

export default SendEmailButton
