import React from 'react'
import PropTypes from 'prop-types'

import { Icon, Popup } from 'semantic-ui-react'


class RequestStatus extends React.Component {

  static NONE = 'NONE'
  static IN_PROGRESS = 'IN_PROGRESS'
  static SUCCEEDED = 'SUCCEEDED'
  static ERROR = 'ERROR'

  static propTypes = {
    status: PropTypes.string,
    errorMessage: PropTypes.string,
  }

  render() {
    switch (this.props.status) {
      case RequestStatus.IN_PROGRESS:
        return <Icon loading name="spinner" style={{ color: '#4183c4' }} />
      case RequestStatus.SUCCEEDED:
        return <Popup
          trigger={
            <Icon name="check circle" style={{ color: '#00C000' }} />
          }
          content="Success"
          position="top center"
          size="small"
        />
      case RequestStatus.ERROR:
        return <Popup
          trigger={
            <Icon name="warning circle" style={{ color: '#F00000' }} />
          }
          content={`Error: ${this.props.errorMessage || ''}`}
          position="top center"
          size="small"
        />
      default:
        return <Icon name="square outline" style={{ color: 'rgba(0, 0, 0, 0.0)' }} />
    }
  }
}

export default RequestStatus
