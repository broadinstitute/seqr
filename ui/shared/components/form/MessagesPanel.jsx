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

const MessagesPanel = ({ info, warnings, errors }) =>
  <MessagePanelContainer>
    {
      info && info.length > 0 &&
      <StyledMessage info>
        {info.map(infoItem => <div key={infoItem}>{infoItem}<br /></div>)}
      </StyledMessage>
    }
    {
      warnings && warnings.length > 0 &&
      <StyledMessage warning>
        {warnings.map(warning => <div key={warning}><b>WARNING:</b> {warning}<br /></div>)}
      </StyledMessage>
    }
    {
      errors && errors.length > 0 &&
      <StyledMessage error>
        {errors.map(error => <div key={error}><b>ERROR:</b> {error}<br /></div>)}
      </StyledMessage>
    }
  </MessagePanelContainer>

MessagesPanel.propTypes = {
  errors: PropTypes.array,
  warnings: PropTypes.array,
  info: PropTypes.array,
}

export default MessagesPanel
