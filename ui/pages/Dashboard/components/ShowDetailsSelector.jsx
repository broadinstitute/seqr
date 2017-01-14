import React from 'react'
import Toggle from '../../../shared/components/form/Toggle'

const ShowDetailsSelector = props =>
  <span>
    <b>Show Details:</b> &nbsp; &nbsp;
    <Toggle
      color="#4183c4"
      isOn={props.showDetails}
      onClick={() => props.onChange(!props.showDetails)}
    />
  </span>

ShowDetailsSelector.propTypes = {
  showDetails: React.PropTypes.bool.isRequired,
  onChange: React.PropTypes.func.isRequired,
}

export default ShowDetailsSelector
