import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { Message } from 'semantic-ui-react'

const MessagePanelContainer = styled.div`
  padding: 5px 10px;
`

const StyledMessage = styled(Message)`
  margin: 10px 0px 30px 0px!important;
  display: block !important;
  text-align: left !important;
`

class MessagesPanel extends React.Component {

  static propTypes = {
    errors: PropTypes.array,
    warnings: PropTypes.array,
    info: PropTypes.array,
  }

  render() {
    return (
      <MessagePanelContainer>
        {
          this.props.info && this.props.info.length > 0 &&
          <StyledMessage info>
            {this.props.info.map(info => <div key={info}>{info}<br /></div>)}
          </StyledMessage>
        }
        {
          this.props.warnings && this.props.warnings.length > 0 &&
          <StyledMessage warning>
            {this.props.warnings.map(warning => <div key={warning}><b>WARNING:</b> {warning}<br /></div>)}
          </StyledMessage>
        }
        {
          this.props.errors && this.props.errors.length > 0 &&
          <StyledMessage error>
            {this.props.errors.map(error => <div key={error}><b>ERROR:</b> {error}<br /></div>)}
          </StyledMessage>
        }
      </MessagePanelContainer>)
  }
}

export default MessagesPanel
