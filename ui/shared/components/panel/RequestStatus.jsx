import React from 'react'
import PropTypes from 'prop-types'
import { Popup } from 'semantic-ui-react'

import { ColoredIcon } from 'shared/components/StyledComponents'

export const NONE = 'NONE'
export const IN_PROGRESS = 'IN_PROGRESS'
export const SUCCEEDED = 'SUCCEEDED'
export const ERROR = 'ERROR'

class RequestStatus extends React.PureComponent {

  static propTypes = {
    status: PropTypes.string,
    errorMessage: PropTypes.string,
  }

  render() {
    const { status, errorMessage } = this.props
    switch (status) {
      case IN_PROGRESS:
        return <ColoredIcon loading name="spinner" color="#4183c4" />
      case SUCCEEDED:
        return (
          <Popup
            trigger={<ColoredIcon name="check circle" color="#00C000" />}
            content="Success"
            position="top center"
            size="small"
          />
        )
      case ERROR:
        return (
          <Popup
            trigger={<ColoredIcon name="warning circle" color="#F00000" />}
            content={`Error: ${errorMessage || ''}`}
            position="top center"
            size="small"
          />
        )
      default:
        return <ColoredIcon name="square outline" color="rgba(0, 0, 0, 0.0)" />
    }
  }

}

export default RequestStatus
