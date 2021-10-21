import React from 'react'
import PropTypes from 'prop-types'

import BaseFieldView from './BaseFieldView'

const EMPTY_DICT = {}

const SingleFieldView = React.memo(props => <BaseFieldView formFieldProps={EMPTY_DICT} {...props} />)

SingleFieldView.propTypes = {
  field: PropTypes.string.isRequired,
}

export default SingleFieldView
