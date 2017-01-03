import React from 'react'
import { Icon, Popup } from 'semantic-ui-react'


class SaveStatus extends React.Component {

  static NONE = 0
  static IN_PROGRESS = 1
  static SUCCEEDED = 2
  static ERROR = 3

  static propTypes = {
    status: React.PropTypes.number,
    errorMessage: React.PropTypes.string,
  }

  render() {
    let icon = null
    let message = ''
    switch (this.props.status) {
      case SaveStatus.IN_PROGRESS:
        icon = <Icon loading name="spinner" style={{ color: '#4183c4' }} />
        message = 'Loading...'
        break
      case SaveStatus.SUCCEEDED:
        icon = <Icon name="check circle" style={{ color: '#00C000' }} />
        message = 'Saved'
        break
      case SaveStatus.ERROR:
        icon = <Icon name="warning circle" style={{ color: '#F00000' }} />
        message = `Error: Unable to save: ${this.props.errorMessage || ''}`
        break
      default:
        icon = <Icon name="square outline" style={{ color: 'rgba(0, 0, 0, 0.0)' }} />
        break
    }

    return <Popup
      trigger={icon}
      content={message}
      positioning="top center"
      size="small"
    />
  }
}

export default SaveStatus
