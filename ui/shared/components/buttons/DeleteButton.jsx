import React from 'react'
import PropTypes from 'prop-types'
import { Icon } from 'semantic-ui-react'

import DispatchRequestButton from './DispatchRequestButton'


const DeleteButton = ({ initialValues, onSubmit, confirmDialog, buttonText }) =>
  <DispatchRequestButton
    buttonContent={<span><Icon link size={buttonText ? null : 'small'} name="trash" />{buttonText}</span>}
    onSubmit={() => onSubmit({ ...initialValues, delete: true })}
    confirmDialog={confirmDialog}
  />

DeleteButton.propTypes = {
  onSubmit: PropTypes.func,
  confirmDialog: PropTypes.string,
  initialValues: PropTypes.object,
  buttonText: PropTypes.string,
}

export default DeleteButton
