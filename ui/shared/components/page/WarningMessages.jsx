import React from 'react'
import PropTypes from 'prop-types'

import { Grid, Message } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { getWarningMessages } from 'redux/selectors'

class WarningMessages extends React.PureComponent {

  static propTypes = {
    warningMessages: PropTypes.arrayOf(PropTypes.object),
  }

  state = { hiddenMessages: {} }

  hide = message => () => {
    this.setState(prevState => ({ ...prevState.hiddenMessages, [message]: true }))
  }

  render() {
    const { warningMessages: allWarningMessages } = this.props
    const { hiddenMessages } = this.state
    const warningMessages = (allWarningMessages || []).filter(({ message }) => !hiddenMessages[message])
    return warningMessages.length > 0 && warningMessages.map(({ header, message }) => (
      <Grid.Row>
        <Grid.Column textAlign="center">
          <Message key={message} header={header} content={message} warning compact onDismiss={this.hide(message)} />
        </Grid.Column>
      </Grid.Row>
    ))
  }

}

const mapStateToProps = state => ({
  warningMessages: getWarningMessages(state),
})

export default connect(mapStateToProps)(WarningMessages)
