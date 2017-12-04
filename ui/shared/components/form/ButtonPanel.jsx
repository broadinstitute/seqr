import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { Button } from 'semantic-ui-react'
import SaveStatus from '../form/SaveStatus'


const ContainerDiv = styled.div`
  margin: 30px 0px 15px 10px;
  text-align: right;
`

const StyledButton = styled(Button)`
  margin-left: 10px !important;
  width: 100px;
`

const StyledSaveStatus = styled(SaveStatus)`
  padding: 0px 5px;
`

class ButtonPanel extends React.Component {

  static propTypes = {
    cancelButtonText: PropTypes.string,
    submitButtonText: PropTypes.string,
    saveStatus: PropTypes.object,
    saveErrorMessage: PropTypes.string,
    handleClose: PropTypes.func,
    handleSave: PropTypes.func,
  }

  render() {
    return (
      <ContainerDiv>
        <StyledButton onClick={this.props.handleClose}>
          {this.props.cancelButtonText || 'Cancel'}
        </StyledButton>
        <StyledButton onClick={this.props.handleSave} type="submit" color="vk">
          {this.props.submitButtonText || 'Submit'}
        </StyledButton>
        <StyledSaveStatus status={this.props.saveStatus} errorMessage={this.props.saveErrorMessage} />
      </ContainerDiv>)
  }
}

export default ButtonPanel
