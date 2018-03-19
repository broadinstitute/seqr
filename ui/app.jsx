import 'react-hot-loader/patch'
import React from 'react'
import ReactDOM from 'react-dom'
import { AppContainer } from 'react-hot-loader'
import { BrowserRouter, Route } from 'react-router-dom'
import { Provider } from 'react-redux'

import BaseLayout from 'shared/components/page/BaseLayout'
import Dashboard from 'pages/Dashboard/Dashboard'
import rootReducer from 'redux/rootReducer'
import { configureStore } from 'redux/utils/configureStore'

import 'semantic-ui-css/semantic-custom.css'
import 'shared/global.css'

ReactDOM.render(
  <Provider store={configureStore(rootReducer)}>
    <AppContainer>
      <BrowserRouter>
        <BaseLayout>
          <Route exact path="/" component={Dashboard} />
          <Route path="/dashboard" component={Dashboard} />
          <Route path="/app.html" component={Dashboard} />
        </BaseLayout>
      </BrowserRouter>
    </AppContainer>
  </Provider>,
  document.getElementById('reactjs-root'),
)
