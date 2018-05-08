import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import HorizontalOnOffToggle from 'shared/components/toggles/HorizontalOnOffToggle'
import { getShowDetails, updateShowDetails } from '../../../reducers'


const ShowDetailsToggle = ({
  showDetails,
  updateState,
}) =>
  <div style={{ whitespace: 'nowrap' }}>
    Show Details:
    &nbsp; &nbsp;
    <HorizontalOnOffToggle
      color="#4183c4"
      isOn={showDetails}
      onClick={() => updateState(!showDetails)}
    />
  </div>


export { ShowDetailsToggle as ShowDetailsToggleComponent }


ShowDetailsToggle.propTypes = {
  showDetails: PropTypes.bool.isRequired,
  updateState: PropTypes.func.isRequired,
}

const mapStateToProps = state => ({
  showDetails: getShowDetails(state),
})

const mapDispatchToProps = {
  updateState: updateShowDetails,
}

export default connect(mapStateToProps, mapDispatchToProps)(ShowDetailsToggle)
