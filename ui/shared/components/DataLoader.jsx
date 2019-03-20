import React from 'react'
import PropTypes from 'prop-types'
import { Loader, Header, Dimmer } from 'semantic-ui-react'

// TODO shared 404 component
const Error404 = () => (<Header size="huge" textAlign="center">Error 404: Not Found</Header>)

class DataLoader extends React.PureComponent
{
  static propTypes = {
    contentId: PropTypes.any,
    content: PropTypes.any,
    loading: PropTypes.bool.isRequired,
    load: PropTypes.func,
    unload: PropTypes.func,
    hideError: PropTypes.bool,
    errorMessage: PropTypes.node,
    children: PropTypes.node,
    reloadOnIdUpdate: PropTypes.bool,
  }

  constructor(props) {
    super(props)

    if (props.load) {
      props.load(props.contentId)
    }
  }

  render() {
    const { loading, content, errorMessage, children, hideError } = this.props
    if (loading) {
      // Loader needs to be in an extra Dimmer to properly show up if it is in a modal (https://github.com/Semantic-Org/Semantic-UI-React/issues/879)
      return <Dimmer inverted active><Loader content="Loading" /></Dimmer>
    }
    else if (errorMessage) {
      return errorMessage
    }
    else if (content) {
      return children
    }
    else if (!hideError) {
      return <Error404 />
    }
    return null
  }

  componentWillUpdate(nextProps) {
    if (nextProps.reloadOnIdUpdate && nextProps.contentId !== this.props.contentId) {
      nextProps.load(nextProps.contentId)
    }
  }

  componentWillUnmount() {
    if (this.props.unload) {
      this.props.unload()
    }
  }
}

export default DataLoader
