import React from 'react'
import PropTypes from 'prop-types'

import DispatchRequestButton from './DispatchRequestButton'
import { ButtonLink } from '../StyledComponents'

const DeleteButton = ({ initialValues, onSubmit, buttonText, size, ...props }) =>
  <DispatchRequestButton
    onSubmit={() => onSubmit({ ...initialValues, delete: true })}
    {...props}
  >
    <ButtonLink content={buttonText} icon="trash" labelPosition={buttonText && 'right'} size={size} />
  </DispatchRequestButton>

DeleteButton.propTypes = {
  onSubmit: PropTypes.func,
  confirmDialog: PropTypes.oneOfType([PropTypes.string, PropTypes.node]),
  initialValues: PropTypes.object,
  buttonText: PropTypes.string,
  size: PropTypes.string,
}

export default DeleteButton
