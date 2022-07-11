import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { Button, Icon } from 'semantic-ui-react'
import RequestStatus from '../panel/RequestStatus'

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
    cancelButtonIcon: PropTypes.string,
    submitButtonText: PropTypes.string,
    submitButtonIcon: PropTypes.string,
    saveStatus: PropTypes.string,
    saveErrorMessage: PropTypes.string,
    handleClose: PropTypes.func,
    handleSave: PropTypes.func,
  }

  render() {
    const {
      handleClose, cancelButtonText, handleSave, submitButtonText, submitButtonIcon, saveStatus, saveErrorMessage,
      cancelButtonIcon,
    } = this.props
    return (
      <ContainerDiv>
        {handleClose && (
          <StyledButton tabIndex={0} onClick={handleClose} type="button">
            {cancelButtonIcon && <Icon name={cancelButtonIcon} />}
            {cancelButtonText || 'Cancel'}
          </StyledButton>
        )}
        <StyledButton tabIndex={0} onClick={handleSave} type="submit" color="blue">
          {submitButtonText || 'Submit'}
          {submitButtonIcon && <Icon name={submitButtonIcon} />}
        </StyledButton>
        <StyledRequestStatus status={saveStatus} errorMessage={saveErrorMessage} />
      </ContainerDiv>
    )
  }

}

export default ButtonPanel
