import React from 'react'

import { Icon, Popup } from 'semantic-ui-react'


class FamilyInfoEditableField extends React.Component {
  static infoDivStyle = {
    paddingLeft: '22px',
    maxWidth: '550px',
    wordWrap: 'break-word',
  }

  static propTypes = {
    isPrivate: React.PropTypes.bool.isRequired,
    isEditable: React.PropTypes.bool.isRequired,
    label: React.PropTypes.string.isRequired,
    initialText: React.PropTypes.string.isRequired,
    submitUrl: React.PropTypes.string.isRequired,
  }

  render() {
    return <span>
      {this.props.isPrivate ?
        <Popup
          trigger={<Icon name="lock" />}
          content="This field is private to internal staff users. External users will not be able to see it."
          positioning="top center"
          size="small"
        /> :
        null
      }
      <b>{this.props.label}: </b>
      <a
        tabIndex="0"
        onClick={() => this.setState({ showModal: true })}
        style={{ paddingLeft: '20px' }}
      >
        <Icon link name="write" />
      </a>
      { this.props.initialText ?
        <span><br />
          <div
            style={this.props.infoDivStyle}
            dangerouslySetInnerHTML={{ __html: this.props.initialText }}
          />
        </span> : <br />
      }
    </span>
  }
}

export default FamilyInfoEditableField
