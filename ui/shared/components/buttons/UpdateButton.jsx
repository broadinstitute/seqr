import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Icon } from 'semantic-ui-react'

import ButtonLink from './ButtonLink'
import ReduxFormWrapper from '../form/ReduxFormWrapper'
import Modal from '../modal/Modal'

const EditLabel = styled.span`
  font-size: ${props => (props.size === 'small' ? '.9em' : '1em')};
  padding-right: 5px;
`

export const IconButtonContent = ({ buttonText, editIconName, size }) =>
  <span>
    {buttonText && <EditLabel size={size}>{buttonText}</EditLabel>}
    <Icon link size={size} name={editIconName || 'write'} />
  </span>

IconButtonContent.propTypes = {
  buttonText: PropTypes.string,
  editIconName: PropTypes.string,
  size: PropTypes.string,
}

const UpdateButton = ({ onSubmit, initialValues, formFields, modalTitle, modalId, buttonText, editIconName, size, formContainer = <div /> }) =>
  <Modal
    title={modalTitle}
    modalName={modalId}
    trigger={<ButtonLink><IconButtonContent buttonText={buttonText} editIconName={editIconName} size={size} /></ButtonLink>}
  >
    {React.cloneElement(formContainer, { children: (
      <ReduxFormWrapper
        onSubmit={onSubmit}
        form={modalId}
        initialValues={initialValues}
        fields={formFields}
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
  size: PropTypes.string,
}

export default UpdateButton
