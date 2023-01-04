import React from 'react'
import PropTypes from 'prop-types'
import { Button, Segment } from 'semantic-ui-react'

class PhiWarningUploadField extends React.PureComponent {

  static propTypes = {
    children: PropTypes.node,
  }

  state = { confirmedNoPhi: false }

  confirmNoPhi = () => {
    this.setState({ confirmedNoPhi: true })
  }

  render() {
    const { confirmedNoPhi } = this.state
    const { children } = this.props
    return confirmedNoPhi ? children : (
      <Segment basic compact textAlign="center" size="large">
        <i>seqr </i>
        is not a HIPAA-compliant platform. By proceeding, I affirm that this image does not contain any
        protected health information (PHI), either in the image itself or in the image metadata.
        <br />
        <br />
        <Button primary floated="right" content="Continue" onClick={this.confirmNoPhi} />
      </Segment>
    )
  }

}

export default PhiWarningUploadField
