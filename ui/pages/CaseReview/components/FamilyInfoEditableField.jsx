import React from 'react'

import { Icon, Popup } from 'semantic-ui-react'
import RichTextEditorModal from '../../../shared/components/RichTextEditorModal'

class FamilyInfoEditableField extends React.Component {
  static propTypes = {
    displayName: React.PropTypes.string.isRequired,
    isPrivate: React.PropTypes.bool.isRequired,
    label: React.PropTypes.string.isRequired,
    initialText: React.PropTypes.string.isRequired,
    submitUrl: React.PropTypes.string.isRequired,
    onSave: React.PropTypes.func.isRequired,
    infoDivStyle: React.PropTypes.object.isRequired,
  }

  constructor(props) {
    super(props)

    this.state = {
      showModal: false,
    }
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
      { this.state.showModal ?
        <RichTextEditorModal
          title={`Family ${this.props.displayName}: ${this.props.label}`}
          initialText={this.props.initialText}
          formSubmitUrl={this.props.submitUrl}
          onClose={() => this.setState({ showModal: false })}
          onSave={(responseJson) => { this.props.onSave(responseJson) }}
        /> : <br />
      }
    </span>
  }
}

export default FamilyInfoEditableField
