import React from 'react'

class InitialSettingsProvider extends React.Component {
  static propTypes = {
    children: React.PropTypes.element.isRequired,
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

    this.initialSettings = {}
    if (!window.initialUrl) {
      //both initialSettings and initialUrl are null, so
      //it's assumed the page doesn't require any initial data
      this.setState({ initialized: true })
      return
    }

    // since initialSettings aren't embedded in the page, retrieve them from server using initialUrl
    fetch(window.initialUrl, { credentials: 'include' })
      .then((response) => {
        console.log(response)
        if (response.status === 401) {
          window.location.href = `/login?next=${window.location.href}`
          return null
        }
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
      const children = React.Children.map(this.props.children,
        child => React.cloneElement(child, { initialSettings: this.initialSettings }))

      if (children.length !== 1) {
        throw new Error(`Exactly 1 child expected. Found ${children.length}.`)
      }
      return children[0]
    }

    if (!this.state.error) {
      console.log('InitialSettingsProvider returning Loading...')
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
