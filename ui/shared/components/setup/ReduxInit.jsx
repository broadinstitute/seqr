/* eslint-disable */

import React from 'react'
import { Provider } from 'react-redux'
import throttle from 'lodash/throttle'

import { configureStore } from '../../utils/configureStore'
import { loadState, saveState } from '../../utils/localStorage'


class ReduxInit extends React.Component {

  static propTypes = {
    storeName: React.PropTypes.string.isRequired,
    rootReducer: React.PropTypes.func.isRequired,
    children: React.PropTypes.object.isRequired,
    getStateToSave: React.PropTypes.func,
    applyRestoredState: React.PropTypes.func,
    initialSettings: React.PropTypes.object,
  }

  constructor(props) {
    super(props)

    this.store = null
  }

  componentWillMount() {
    if (this.store === null) {

      let initialSettings = this.props.initialSettings
      if (this.props.applyRestoredState) {
        const savedState = loadState(this.props.storeName)
        initialSettings = this.props.applyRestoredState(this.props.initialSettings || {}, savedState)
      }

      this.store = configureStore(
        this.props.storeName,
        this.props.rootReducer,
        initialSettings)
    }

    if (this.props.getStateToSave) {
      this.store.subscribe(throttle(() => {
        saveState(
          this.props.storeName,
          this.props.getStateToSave(this.store.getState()),
        )
      }, 500))
    }
  }

  render = () =>
    <Provider store={this.store}>
      { this.props.children }
    </Provider>
}

export default ReduxInit
