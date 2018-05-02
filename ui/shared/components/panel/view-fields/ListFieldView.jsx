import React from 'react'
import PropTypes from 'prop-types'

import BaseFieldView from './BaseFieldView'

const ListFieldView = (props) => {
  const { formatValue, ...baseProps } = props
  return <BaseFieldView fieldDisplay={values => values.map(formatValue).join(', ')} {...baseProps} />
}

ListFieldView.propTypes = {
  formatValue: PropTypes.func,
}

export default ListFieldView
