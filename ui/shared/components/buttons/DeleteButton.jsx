import React from 'react'
import PropTypes from 'prop-types'

import DispatchRequestButton from './DispatchRequestButton'

const DeleteButton = ({ initialValues, onSubmit, buttonText, ...props }) =>
  <DispatchRequestButton
    onSubmit={() => onSubmit({ ...initialValues, delete: true })}
    buttonContent={buttonText}
    icon="trash"
    labelPosition={buttonText && 'right'}
    {...props}
  />

DeleteButton.propTypes = {
  onSubmit: PropTypes.func,
  confirmDialog: PropTypes.oneOfType([PropTypes.string, PropTypes.node]),
  initialValues: PropTypes.object,
  buttonText: PropTypes.string,
  size: PropTypes.string,
}

export default DeleteButton
