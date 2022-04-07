import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Form } from 'semantic-ui-react'

import { updateFilter } from '../reducers'
import { getProjectFilter, getCategoryOptions } from '../selectors'

const FilterContainer = styled.span`
  display: inline-block;
`

const FilterSelector = React.memo(({ filter, options, onChange }) => (
  <FilterContainer>
    <Form.Select
      name="filterSelector"
      value={filter}
      onChange={onChange}
      options={options}
    />
  </FilterContainer>
))

export { FilterSelector as FilterSelectorComponent }

FilterSelector.propTypes = {
  filter: PropTypes.string.isRequired,
  options: PropTypes.arrayOf(PropTypes.object),
  onChange: PropTypes.func.isRequired,
}

const mapStateToProps = state => ({
  filter: getProjectFilter(state),
  options: getCategoryOptions(state),
})

const mapDispatchToProps = { onChange: (event, data) => updateFilter(data.value) }

export default connect(mapStateToProps, mapDispatchToProps)(FilterSelector)
