import React from 'react'
import PropTypes from 'prop-types'

import DispatchRequestButton from './DispatchRequestButton'

const submitDelete = (onSubmit, initialValues = {}) => () => onSubmit({ ...initialValues, delete: true })

const DeleteButton = React.memo(({ initialValues, onSubmit, buttonText, size, ...props }) => (
  <DispatchRequestButton
    onSubmit={submitDelete(onSubmit, initialValues)}
    buttonContent={buttonText}
    icon="trash"
    labelPosition={buttonText && 'right'}
    size={size || 'small'}
    {...props}
  />
))

DeleteButton.propTypes = {
  onSubmit: PropTypes.func,
  confirmDialog: PropTypes.oneOfType([PropTypes.string, PropTypes.node]),
  initialValues: PropTypes.object,
  buttonText: PropTypes.string,
  size: PropTypes.string,
}

export default DeleteButton
