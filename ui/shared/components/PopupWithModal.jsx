import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Popup } from 'semantic-ui-react'

import { getOpenModals } from 'redux/utils/modalReducer'

const BehindModalPopup = styled(Popup)`
  z-index: 500 !important;
`

class PopupWithModal extends React.PureComponent {

  static propTypes = {
    openModal: PropTypes.bool,
  }

  state = { isOpen: false }

  handleOpen = () => {
    this.setState({ isOpen: true })
  }

  handleClose = () => {
    if (!this.props.openModal) {
      this.setState({ isOpen: false })
    }
  }

  render() {
    const { openModal, ...popupProps } = this.props
    return (
      <BehindModalPopup
        {...popupProps}
        open={this.state.isOpen}
        onClose={this.handleClose}
        onOpen={this.handleOpen}
      />
    )
  }

}

const mapStateToProps = state => ({
  openModal: getOpenModals(state).length > 0,
})

export default connect(mapStateToProps)(PopupWithModal)
