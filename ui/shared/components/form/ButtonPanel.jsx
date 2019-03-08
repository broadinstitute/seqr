import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { Button } from 'semantic-ui-react'
import RequestStatus from '../form/RequestStatus'


const ContainerDiv = styled.div`
  position: absolute;
  bottom: 0;
  right: 0;
`

const StyledButton = styled(Button)`
  margin-left: 10px !important;
  width: 100px;
`

const StyledRequestStatus = styled(RequestStatus)`
  padding: 0px 5px;
`

class ButtonPanel extends React.PureComponent {

  static propTypes = {
    cancelButtonText: PropTypes.string,
    submitButtonText: PropTypes.string,
    saveStatus: PropTypes.string,
    saveErrorMessage: PropTypes.string,
    handleClose: PropTypes.func,
    handleSave: PropTypes.func,
  }

  render() {
    return (
      <ContainerDiv>
        {this.props.handleClose &&
          <StyledButton tabIndex={0} onClick={this.props.handleClose} type="button">
            {this.props.cancelButtonText || 'Cancel'}
          </StyledButton>
        }
        <StyledButton tabIndex={0} onClick={this.props.handleSave} type="submit" color="blue">
          {this.props.submitButtonText || 'Submit'}
        </StyledButton>
        <StyledRequestStatus status={this.props.saveStatus} errorMessage={this.props.saveErrorMessage} />
      </ContainerDiv>)
  }
}

export default ButtonPanel
