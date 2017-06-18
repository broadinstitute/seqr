/* eslint global-require: 0 */
/* eslint react/no-multi-comp: 0 */
/* eslint import/no-mutable-exports: 0 */

import React from 'react'
import PropTypes from 'prop-types'

import visualizeRender from 'react-render-visualizer-decorator'
import Perf from 'react-addons-perf'

window.Perf = Perf

//Perf.start()
//Perf.stop()
//Perf.printWasted()

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
      return <Profiler>
        {this.props.children}
      </Profiler>
    }

    return this.props.children
  }
}

export default Wrapper
