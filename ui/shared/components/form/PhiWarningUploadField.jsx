import React from 'react'
import PropTypes from 'prop-types'
import { Button, Segment } from 'semantic-ui-react'

class PhiWarningUploadField extends React.PureComponent {

  static propTypes = {
    children: PropTypes.node,
    fileDescriptor: PropTypes.string,
    disclaimerDetail: PropTypes.string,
  }

  state = { confirmedNoPhi: false }

  confirmNoPhi = () => {
    this.setState({ confirmedNoPhi: true })
  }

  render() {
    const { confirmedNoPhi } = this.state
    const { children, fileDescriptor, disclaimerDetail } = this.props
    return confirmedNoPhi ? children : (
      <Segment basic compact textAlign="center" size="large">
        <i>seqr </i>
        is not a HIPAA-compliant platform. By proceeding, I affirm that this &nbsp;
        {fileDescriptor}
        &nbsp; does not contain any protected health information (PHI), &nbsp;
        {disclaimerDetail}
        <br />
        <br />
        <Button primary floated="right" content="I Agree" onClick={this.confirmNoPhi} />
      </Segment>
    )
  }

}

export default PhiWarningUploadField
