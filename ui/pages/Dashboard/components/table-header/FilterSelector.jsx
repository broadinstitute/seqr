/* eslint-disable react/no-unused-prop-types */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import {Dropdown, Form} from 'semantic-ui-react'

import { getProjectCategoriesByGuid } from 'redux/rootReducer'
import { getProjectFilter, updateFilter } from '../../reducers'
import {
  SHOW_ALL,
} from '../../constants'

const FilterContainer = styled.span`
  display: inline-block;
  min-width: 8em;
`

const FilterDropdown = styled(Form.Field)`
  display: inline-block;
  padding: 0px !important;
`

const FilterSelector = props =>
  <FilterContainer>
    <FilterDropdown
      selection
      fluid
      name="filterSelector"
      value={props.filter}
      onChange={(event, data) => {
        props.onChange(data.value)
      }}
      options={[
        { value: SHOW_ALL, text: 'All', key: SHOW_ALL },
        ...Object.values(props.projectCategoriesByGuid).map(projectCategory => ({ value: projectCategory.guid, text: projectCategory.name, key: projectCategory.guid })),
      ]}
    />
  </FilterContainer>

export { FilterSelector as FilterSelectorComponent }

FilterSelector.propTypes = {
  filter: PropTypes.string.isRequired,
  projectCategoriesByGuid: PropTypes.object,
  onChange: PropTypes.func.isRequired,
}

const mapStateToProps = state => ({
  filter: getProjectFilter(state),
  projectCategoriesByGuid: getProjectCategoriesByGuid(state),
})

const mapDispatchToProps = { onChange: updateFilter }

export default connect(mapStateToProps, mapDispatchToProps)(FilterSelector)
