import React from 'react'
import PropTypes from 'prop-types'

import VerticalArrowToggle from 'shared/components/toggles/VerticalArrowToggle'

const SortDirectionToggle = ({
  value,
  onChange,
}) => <VerticalArrowToggle
  onClick={() => onChange(-1 * value)}
  isPointingDown={value === 1}
/>

SortDirectionToggle.propTypes = {
  value: PropTypes.number.isRequired,
  onChange: PropTypes.func.isRequired,
}

export default SortDirectionToggle
