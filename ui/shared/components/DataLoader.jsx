import React from 'react'
import PropTypes from 'prop-types'
import { Loader, Header, Dimmer } from 'semantic-ui-react'

// TODO shared 404 component
const Error404 = () => (<Header size="huge" textAlign="center">Error 404: Not Found</Header>)

class DataLoader extends React.Component
{
  static propTypes = {
    contentId: PropTypes.string.isRequired,
    content: PropTypes.any,
    loading: PropTypes.bool.isRequired,
    load: PropTypes.func.isRequired,
    children: PropTypes.node,
  }

  constructor(props) {
    super(props)

    props.load(props.contentId)
  }

  render() {
    const { loading, content, children } = this.props
    if (loading) {
      // Loader needs to be in an extra Dimmer to properly show up if it is in a modal (https://github.com/Semantic-Org/Semantic-UI-React/issues/879)
      return <Dimmer inverted active><Loader content="Loading" /></Dimmer>
    }
    else if (content) {
      return children
    }
    return <Error404 />
  }
}

export default DataLoader
