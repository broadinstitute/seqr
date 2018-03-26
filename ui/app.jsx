import 'react-hot-loader/patch'
import React from 'react'
import ReactDOM from 'react-dom'
import { AppContainer } from 'react-hot-loader'
import { BrowserRouter, Route } from 'react-router-dom'
import { Provider } from 'react-redux'

import BaseLayout from 'shared/components/page/BaseLayout'
import Dashboard from 'pages/Dashboard/Dashboard'
import Project from 'pages/Project/Project'
import rootReducer from 'redux/rootReducer'
import { configureStore } from 'redux/utils/configureStore'

import 'semantic-ui-css/semantic-custom.css'
import 'shared/global.css'

ReactDOM.render(
  <Provider store={configureStore(rootReducer, window.initialJSON || { user: {} })}>
    <AppContainer>
      <BrowserRouter>
        <BaseLayout>
          <Route exact path="/" component={Dashboard} />
          <Route path="/dashboard" component={Dashboard} />
          <Route exact path="/app.html" component={Dashboard} />
          <Route path="/project/:projectGuid" component={Project} />
          <Route path="/app.html?projectGuid=:projectGuid" component={Project} />
        </BaseLayout>
      </BrowserRouter>
    </AppContainer>
  </Provider>,
  document.getElementById('reactjs-root'),
)
