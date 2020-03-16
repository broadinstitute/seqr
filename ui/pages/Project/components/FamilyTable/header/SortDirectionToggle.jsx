import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Button } from 'semantic-ui-react'

const SortButton = styled(Button)`
  &.ui.basic.button {
    box-shadow: none !important;
    padding: 0 !important;
  }
`

const SortDirectionToggle = React.memo(({ value, onChange }) =>
  <SortButton
    circular
    basic
    onClick={() => onChange(-1 * value)}
    size="small"
    icon={`arrow ${value === 1 ? 'down' : 'up'}`}
  />,
)

SortDirectionToggle.propTypes = {
  value: PropTypes.number.isRequired,
  onChange: PropTypes.func.isRequired,
}

export default SortDirectionToggle
