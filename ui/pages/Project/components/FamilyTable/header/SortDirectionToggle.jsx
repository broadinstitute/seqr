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

const toggleSort = (value, onChange) => () => onChange(-1 * value)

const SortDirectionToggle = React.memo(({ value, onChange }) => (
  <SortButton
    circular
    basic
    onClick={toggleSort(value, onChange)}
    size="small"
    icon={`arrow ${value === 1 ? 'down' : 'up'}`}
  />
))

SortDirectionToggle.propTypes = {
  value: PropTypes.number.isRequired,
  onChange: PropTypes.func.isRequired,
}

export default SortDirectionToggle
