import React from 'react'
import PropTypes from 'prop-types'

import BaseFieldView from './BaseFieldView'

const PlainTextFieldView = (props) => {
  const fields = [{ name: props.field }]
  return <BaseFieldView
    formFields={fields}
    {...props}
  />
}

PlainTextFieldView.propTypes = {
  field: PropTypes.string.isRequired,
}

export default PlainTextFieldView
