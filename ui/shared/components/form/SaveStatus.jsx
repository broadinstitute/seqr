import React from 'react'
import PropTypes from 'prop-types'

import { Icon, Popup } from 'semantic-ui-react'


class SaveStatus extends React.Component {

  static NONE = 0
  static IN_PROGRESS = 1
  static SUCCEEDED = 2
  static ERROR = 3

  static propTypes = {
    status: PropTypes.number,
    errorMessage: PropTypes.string,
  }

  render() {
    switch (this.props.status) {
      case SaveStatus.IN_PROGRESS:
        return <Icon loading name="spinner" style={{ color: '#4183c4' }} />
      case SaveStatus.SUCCEEDED:
        return <Popup
          trigger={
            <Icon name="check circle" style={{ color: '#00C000' }} />
          }
          content="Saved"
          position="top center"
          size="small"
        />
      case SaveStatus.ERROR:
        return <Popup
          trigger={
            <Icon name="warning circle" style={{ color: '#F00000' }} />
          }
          content={`Error: Unable to save: ${this.props.errorMessage || ''}`}
          position="top center"
          size="small"
        />
      default:
        return <Icon name="square outline" style={{ color: 'rgba(0, 0, 0, 0.0)' }} />
    }
  }
}

export default SaveStatus
