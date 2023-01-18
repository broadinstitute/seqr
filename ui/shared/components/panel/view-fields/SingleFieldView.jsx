import React from 'react'
import PropTypes from 'prop-types'

import BaseFieldView from './BaseFieldView'

const FIELD_PROPS = {
  // Override default behavior for undefined values, which is to exclude them from form values
  parse: val => val || null,
}

const SingleFieldView = React.memo(props => <BaseFieldView formFieldProps={FIELD_PROPS} {...props} />)

SingleFieldView.propTypes = {
  field: PropTypes.string.isRequired,
}

export default SingleFieldView
