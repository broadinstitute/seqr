import React from 'react'
import PropTypes from 'prop-types'
import { Loader, Dimmer } from 'semantic-ui-react'

import { Error404 } from 'shared/components/page/Errors'


class DataLoader extends React.PureComponent
{
  static propTypes = {
    contentId: PropTypes.any,
    content: PropTypes.any,
    loading: PropTypes.bool.isRequired,
    load: PropTypes.func,
    unload: PropTypes.func,
    initialLoad: PropTypes.func,
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
    if (props.initialLoad) {
      props.initialLoad(props.contentId)
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
