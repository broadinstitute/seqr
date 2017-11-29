import React from 'react'
import PropTypes from 'prop-types'


class InitialSettingsProvider extends React.Component {
  static propTypes = {
    children: PropTypes.node,
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
      this.setState({ initialized: true })
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
        //console.log(response)
        if (response.status === 401) {
          window.location.href = `/login?next=${window.location.href}`
          return null
        }
        if (response.ok) {
          try {
            return response.json()
          } catch (exception) {
            const message = `Error while parsing ${window.initialUrl} response.`
            console.log(message, exception)
            this.setState({ initialized: false, error: message })
          }
        }
        this.setState({ initialized: false, error: `${window.initialUrl} ${response.statusText.toLowerCase()} (${response.status})` })
        return {}
      })
      .then((responseJSON) => {
        console.log('Received initial settings:')
        console.log(responseJSON)
        this.initialSettings = responseJSON
        window.initialJSON = responseJSON //simplifies debugging
        this.setState({ initialized: true })
      })
      /*
      .catch((exception) => {
        this.setState({ initialized: false, error: exception.message })
      })
      */
  }

  render() {
    if (this.state.initialized) {
      const children = React.Children.map(this.props.children,
        child => React.cloneElement(child, { initialSettings: this.initialSettings }))

      if (children.length !== 1) {
        console.error(`Exactly 1 child expected. Found ${children.length}.`, children)
      }
      return children[0]
    }

    //if (!this.state.error) {
    //  console.log('returning this state', this.state)
    //}

    if (!this.state.error) {
      return <div style={{ padding: '100px', width: '100%' }}><center>Loading ...</center></div>
    }
    return <div style={{ padding: '100px', width: '100%' }}><center>{`Error: ${this.state.error}`}</center></div>
  }
}

export default InitialSettingsProvider
