import React from 'react'


class InitialSettingsProvider extends React.Component {
  static propTypes = {
    children: React.PropTypes.element.isRequired,  //require 1 child component
  }

  constructor(props) {
    super(props)

    this.state = {
      initialized: false,
      error: null,
    }
  }

  componentWillMount() {
    // check if initialSettings already embedded in page
    if (window.initialJSON) {
      this.initialSettings = window.initialJSON
      this.setState({
        initialized: true,
      })
      return
    }

    // retrieve initialSettings from server since they weren't embedded in the page
    this.initialSettings = {}
    if (!window.initialUrl) {
      this.setState({ initialized: true })
      return
    }

    fetch(window.initialUrl, { credentials: 'include' })
      .then((response) => {
        if (response.ok) {
          return response.json()
        }
        throw new Error(`initialURL: ${window.initialUrl} ${response.statusText.toLowerCase()} (${response.status})`)
      })
      .then((responseJSON) => {
        console.log('Initial settings: ', responseJSON)
        this.initialSettings = responseJSON
        this.setState({ initialized: true })
      })
      .catch((exception) => {
        this.setState({ error: exception.message.toString() })
      })
  }

  render() {
    if (this.state.initialized) {
      return <div>{
          React.cloneElement(this.props.children, {
            initialSettings: this.initialSettings,
          })
      }
      </div>
    }

    if (!this.state.error) {
      return <div style={{ padding: '100px', width: '100%' }}><center>Loading ...</center></div>
    }

    console.log('Returning error', this.state.error)
    return <div style={{ padding: '100px', width: '100%' }}>
      <center>
        <b>Error:</b><br />
        {this.state.error}
      </center>
    </div>
  }
}

export default InitialSettingsProvider
