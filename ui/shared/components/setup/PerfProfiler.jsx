/* eslint global-require: 0 */
/* eslint react/no-multi-comp: 0 */
/* eslint import/no-mutable-exports: 0 */

import React from 'react'
import visualizeRender from 'react-render-visualizer-decorator'
import Perf from 'react-addons-perf'

window.Perf = Perf

//Perf.start()
//Perf.stop()
//Perf.printWasted()

@visualizeRender
class Profiler extends React.Component {
  static propTypes = {
    children: React.PropTypes.element.isRequired,
  }

  render = () => {
    return this.props.children
  }
}

class Wrapper extends React.Component {
  static propTypes = {
    enableVisualizeRender: React.PropTypes.bool.isRequired,
    enableWhyDidYouUpdate: React.PropTypes.bool.isRequired,
    children: React.PropTypes.element.isRequired,
  }

  constructor = () => {
    if (this.props.enableWhyDidYouUpdate && process.env.NODE_ENV !== 'production') {
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
