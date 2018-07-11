import React from 'react'
import PropTypes from 'prop-types'

import DispatchRequestButton from './DispatchRequestButton'
import { IconButtonContent } from './UpdateButton'

const DeleteButton = ({ initialValues, onSubmit, confirmDialog, buttonText, size }) =>
  <DispatchRequestButton
    buttonContent={<IconButtonContent editIconName="trash" buttonText={buttonText} size={size} />}
    onSubmit={() => onSubmit({ ...initialValues, delete: true })}
    confirmDialog={confirmDialog}
  />

DeleteButton.propTypes = {
  onSubmit: PropTypes.func,
  confirmDialog: PropTypes.string,
  initialValues: PropTypes.object,
  buttonText: PropTypes.string,
  size: PropTypes.string,
}

export default DeleteButton
