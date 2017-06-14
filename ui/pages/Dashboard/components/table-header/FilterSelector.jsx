/* eslint-disable react/no-unused-prop-types */

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getProjectFilter, getProjectCategoriesByGuid, updateFilter } from '../../reducers/rootReducer'
import {
  SHOW_ALL,
} from '../../constants'


const FilterSelector = props =>
  <div style={{ display: 'inline' }}>
    <select
      name="filterSelector"
      value={props.filter}
      onChange={event => props.onChange(event.target.value)}
      style={{ display: 'inline', padding: '0px !important' }}
    >
      <option value={SHOW_ALL}>All</option>
      {
        Object.values(props.projectCategoriesByGuid).map((projectCategory) => {
          return <option key={projectCategory.guid} value={projectCategory.guid}>{projectCategory.name}</option>
        })
      }
    </select>
  </div>

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
