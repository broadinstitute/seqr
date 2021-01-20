import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch } from 'react-router-dom'

import { getUser } from 'redux/selectors'
import { Error404, Error401 } from 'shared/components/page/Errors'

import ElasticsearchStatus from './components/ElasticsearchStatus'
import SampleQc from './components/SampleQc'
import Users from './components/Users'

const IFRAME_STYLE = { position: 'fixed', left: '0', top: '95px' }

export const DATA_MANAGEMENT_PAGES = [
  { path: 'elasticsearch_status', component: ElasticsearchStatus },
  { path: 'kibana', component: () => <iframe width="100%" height="100%" style={IFRAME_STYLE} src="/app/kibana" /> },
  { path: 'sample_qc', component: SampleQc },
  { path: 'users', component: Users },
]

const DataManagement = ({ match, user }) => (
  user.isDataManager ? (
    <Switch>
      {DATA_MANAGEMENT_PAGES.map(({ path, params, component }) =>
        <Route key={path} path={`${match.url}/${path}${params || ''}`} component={component} />,
      )}
      <Route path={match.url} component={null} />
      <Route component={() => <Error404 />} />
    </Switch>
  ) : <Error401 />
)

DataManagement.propTypes = {
  user: PropTypes.object,
  match: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(DataManagement)
