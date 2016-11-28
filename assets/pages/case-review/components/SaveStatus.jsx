import React from 'react'
import { Icon } from 'semantic-ui-react'


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
    switch (this.props.status) {
      case SaveStatus.IN_PROGRESS:
        return <Icon loading size="medium" name="spinner" style={{ color: '#4183c4' }} title="Loading..." />
      case SaveStatus.SUCCEEDED:
        return <Icon size="medium" name="check circle" style={{ color: '#00C000' }} title="Saved" />
      case SaveStatus.ERROR:
        return <Icon size="medium" name="warning circle" style={{ color: '#F00000' }} title={`${this.props.errorMessage || ''}`} />
      default:
        return <Icon size="medium" name="square outline" style={{ color: 'rgba(0, 0, 0, 0.0)' }} />
    }
  }
}

export default SaveStatus
