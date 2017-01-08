import React from 'react'

class FamilyInfoField extends React.Component {
  static propTypes = {
    label: React.PropTypes.string.isRequired,
    initialText: React.PropTypes.string.isRequired,
    infoDivStyle: React.PropTypes.object.isRequired,
  }

  render() {
    return this.props.initialText ?
      <div>
        <b>{this.props.label}:</b> <br />
        <div
          style={this.props.infoDivStyle}
          dangerouslySetInnerHTML={{ __html: this.props.initialText }}
        /><br />
      </div> :
      null
  }
}

export default FamilyInfoField
