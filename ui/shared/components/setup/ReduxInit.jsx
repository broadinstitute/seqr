import React from 'react'
import { Provider } from 'react-redux'

import { configureStore } from '../../utils/configureStore'

class ReduxInit extends React.Component {

  static propTypes = {
    storeName: React.PropTypes.string.isRequired,
    rootReducer: React.PropTypes.func.isRequired,
    children: React.PropTypes.object.isRequired,
    initialSettings: React.PropTypes.object,
  }

  constructor(props) {
    super(props)

    this.store = null
  }

  componentWillMount() {
    if (this.store === null) {
      this.store = configureStore(
        this.props.storeName,
        this.props.rootReducer,
        this.props.initialSettings)
    }
  }

  render = () =>
    <Provider store={this.store}>
      { this.props.children }
    </Provider>
}

export default ReduxInit
