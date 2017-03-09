/* eslint-disable react/no-unused-prop-types */

import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { updateFilter } from '../reducers/rootReducer'
import {
  SHOW_ALL,
  //SHOW_NEW,
} from '../constants'


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

FilterSelector.propTypes = {
  filter: React.PropTypes.string.isRequired,
  projectCategoriesByGuid: React.PropTypes.object,
  onChange: React.PropTypes.func.isRequired,
}

const mapStateToProps = state => ({
  filter: state.projectsTableState.filter,
  projectCategoriesByGuid: state.projectCategoriesByGuid,
})

const mapDispatchToProps = dispatch => bindActionCreators({ onChange: updateFilter }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(FilterSelector)
