import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { getShowDetails, updateShowDetails } from '../../reducers/rootReducer'
import HorizontalOnOffToggle from '../../../../shared/components/form/HorizontalOnOffToggle'


const ShowDetailsToggle = ({
  showDetails,
  updateState,
}) => <div className="nowrap">
  <b>Show Details:</b>
  &nbsp; &nbsp;
  <HorizontalOnOffToggle
    color="#4183c4"
    isOn={showDetails}
    onClick={() => updateState(!showDetails)}
  />
</div>


export { ShowDetailsToggle as ShowDetailsToggleComponent }


ShowDetailsToggle.propTypes = {
  showDetails: React.PropTypes.bool.isRequired,
  updateState: React.PropTypes.func.isRequired,
}

const mapStateToProps = state => ({
  showDetails: getShowDetails(state),
})

const mapDispatchToProps = dispatch => bindActionCreators({
  updateState: updateShowDetails,
}, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(ShowDetailsToggle)
