import 'react-hot-loader/patch'
import React from 'react'
import ReactDOM from 'react-dom'
import { AppContainer } from 'react-hot-loader'
import { BrowserRouter, Route } from 'react-router-dom'
import { Provider } from 'react-redux'
import { createStore } from 'redux'

import BaseLayout from 'shared/components/page/BaseLayout'

import 'semantic-ui-css/semantic-custom.css'
import 'shared/global.css'

import rootReducer from 'redux/rootReducer'
import Dashboard from 'pages/Dashboard/Dashboard'

const store = createStore(rootReducer)

ReactDOM.render(
  <Provider store={store}>
    <AppContainer>
      <BrowserRouter>
        <BaseLayout>
          <Route path="/app.html" component={Dashboard} />
        </BaseLayout>
      </BrowserRouter>
    </AppContainer>
  </Provider>,
  document.getElementById('reactjs-root'),
)
