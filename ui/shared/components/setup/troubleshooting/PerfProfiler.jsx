/* eslint-disable global-require */
/* eslint-disable react/no-multi-comp */
/* eslint-disable import/no-mutable-exports */
/* eslint-disable import/no-extraneous-dependencies */

import React from 'react'
import PropTypes from 'prop-types'

import visualizeRender from 'react-render-visualizer-decorator'


@visualizeRender
class Profiler extends React.Component {
  static propTypes = {
    children: PropTypes.element.isRequired,
  }

  render = () => {
    return this.props.children
  }
}

class Wrapper extends React.Component {
  static propTypes = {
    enableVisualizeRender: PropTypes.bool.isRequired,
    enableWhyDidYouUpdate: PropTypes.bool.isRequired,
    children: PropTypes.element.isRequired,
  }

  constructor(props) {
    super(props)

    if (props.enableWhyDidYouUpdate && process.env.NODE_ENV !== 'production') {
      const { whyDidYouUpdate } = require('why-did-you-update')
      whyDidYouUpdate(React)
    }
  }

  render = () => {
    if (this.props.enableVisualizeRender && process.env.NODE_ENV !== 'production') {
      return (
        <Profiler>
          {this.props.children}
        </Profiler>
      )
    }

    return this.props.children
  }
}

export default Wrapper
