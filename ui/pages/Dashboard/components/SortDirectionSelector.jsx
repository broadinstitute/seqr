import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { Popup } from 'semantic-ui-react'

import { updateSortDirection } from '../reducers/projectsTableReducer'
import { SortDirectionToggle } from '../../../shared/components/form/Toggle'


const SortDirectionSelector = props =>
  <Popup
    trigger={
      <span style={{ paddingLeft: '7px' }}>
        <SortDirectionToggle
          style={{ marginLeft: '30px' }}
          onClick={() => props.onChange(-1 * props.sortDirection)}
          isPointingDown={props.sortDirection === 1}
        />
      </span>
    }
    content={`Sort order: ${props.sortDirection === 1 ? 'Ascending' : 'Descending'}`}
    positioning="top center"
    size="small"
  />

SortDirectionSelector.propTypes = {
  sortDirection: React.PropTypes.number.isRequired,
  onChange: React.PropTypes.func.isRequired,
}


const mapStateToProps = state => ({ sortDirection: state.projectsTable.sortDirection })

const mapDispatchToProps = dispatch => bindActionCreators({ onChange: updateSortDirection }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(SortDirectionSelector)
