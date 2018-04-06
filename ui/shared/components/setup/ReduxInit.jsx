import React from 'react'
import PropTypes from 'prop-types'

import { Provider } from 'react-redux'
import throttle from 'lodash/throttle'

import { configureStore } from '../../../redux/utils/configureStore'
import { loadState, saveState } from '../../utils/localStorage'


class ReduxInit extends React.Component {

  static propTypes = {
    storeName: PropTypes.string.isRequired,
    rootReducer: PropTypes.func.isRequired,
    children: PropTypes.node,
    getStateToSave: PropTypes.func,
    applyRestoredState: PropTypes.func,
    initialSettings: PropTypes.object,
  }

  constructor(props) {
    super(props)

    this.store = null
  }

  componentWillMount() {
    if (this.store === null) {
      let { initialSettings } = this.props
      if (this.props.applyRestoredState) {
        const savedState = loadState(this.props.storeName)
        initialSettings = this.props.applyRestoredState(this.props.initialSettings || {}, savedState)
      }

      this.store = configureStore(
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
      <span>
        { this.props.children }
      </span>
    </Provider>
}

export default ReduxInit
