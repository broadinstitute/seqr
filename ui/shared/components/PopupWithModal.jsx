import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Popup } from 'semantic-ui-react'

import { getOpenModals } from 'redux/utils/modalReducer'

export const BehindModalPopup = styled(Popup)`
  z-index: 500 !important;
`

class PopupWithModal extends React.PureComponent {

  static propTypes = {
    openModal: PropTypes.bool,
    dispatch: PropTypes.func,
  }

  static defaultProps = {
    openModal: null,
    dispatch: null,
  }

  state = { isOpen: false }

  handleOpen = () => {
    this.setState({ isOpen: true })
  }

  handleClose = () => {
    const { openModal } = this.props
    if (!openModal) {
      this.setState({ isOpen: false })
    }
  }

  render() {
    const { openModal, dispatch, ...popupProps } = this.props
    const { isOpen } = this.state
    return (
      <BehindModalPopup
        {...popupProps}
        open={isOpen}
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
