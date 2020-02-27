import React from 'react'
import PropTypes from 'prop-types'

import BaseFieldView from './BaseFieldView'

const SingleFieldView = React.memo((props) => {
  const fields = [{ name: props.field }]
  return <BaseFieldView
    formFields={fields}
    {...props}
  />
})

SingleFieldView.propTypes = {
  field: PropTypes.string.isRequired,
}

export default SingleFieldView
