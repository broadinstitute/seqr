import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch } from 'react-router-dom'

import { getUser, getElasticsearchEnabled } from 'redux/selectors'
import { Error404, Error401 } from 'shared/components/page/Errors'

import AddIGV from './components/AddIGV'
import ElasticsearchStatus from './components/ElasticsearchStatus'
import LoadData from './components/LoadData'
import RnaSeq from './components/RnaSeq'
import Users from './components/Users'
import PhenotypePrioritization from './components/PhenotypePrioritization'
import TRIGGER_DAG_PAGES from './components/TriggerDagPages'

const IFRAME_STYLE = { position: 'fixed', left: '0', top: '95px' }

const PM_DATA_MANAGEMENT_PAGES = [
  { path: 'load_data', component: LoadData },
  { path: 'add_igv', component: AddIGV },
  { path: 'rna_seq', component: RnaSeq },
]

const DATA_MANAGEMENT_PAGES = [
  ...PM_DATA_MANAGEMENT_PAGES,
  { path: 'users', component: Users },
  { path: 'phenotype_prioritization', component: PhenotypePrioritization },
]

const IframePage = ({ title, src }) => <iframe width="100%" height="100%" title={title} style={IFRAME_STYLE} src={src} />

IframePage.propTypes = {
  title: PropTypes.string,
  src: PropTypes.string,
}

const ES_DATA_MANAGEMENT_PAGES = [
  { path: 'elasticsearch_status', component: ElasticsearchStatus },
  {
    path: 'kibana',
    component: () => <IframePage title="Kibana" src="/app/kibana" />,
  },
  ...DATA_MANAGEMENT_PAGES,
]

const LOCAL_HAIL_SEARCH_DATA_MANAGEMENT_PAGES = [
  ...DATA_MANAGEMENT_PAGES,
  { path: 'pipeline_status', component: () => <IframePage title="Loading UI" src="/luigi_ui/static/visualiser/index.html" /> },
]

const AIRFLOW_HAIL_SEARCH_DATA_MANAGEMENT_PAGES = [
  ...DATA_MANAGEMENT_PAGES,
  ...TRIGGER_DAG_PAGES,
]

const dataManagementPages = (user, elasticsearchEnabled) => {
  if (!user.isDataManager) {
    return PM_DATA_MANAGEMENT_PAGES
  }
  if (elasticsearchEnabled) {
    return ES_DATA_MANAGEMENT_PAGES
  }
  return user.isAnvil ? AIRFLOW_HAIL_SEARCH_DATA_MANAGEMENT_PAGES : LOCAL_HAIL_SEARCH_DATA_MANAGEMENT_PAGES
}

const DataManagement = ({ match, user, pages }) => (
  (user.isDataManager || user.isPm) ? (
    <Switch>
      {pages.map(({ path, params, component }) => (
        <Route key={path} path={`${match.url}/${path}${params || ''}`} component={component} />))}
      <Route exact path={match.url} component={null} />
      <Route component={Error404} />
    </Switch>
  ) : <Error401 />
)

DataManagement.propTypes = {
  user: PropTypes.object,
  match: PropTypes.object,
  pages: PropTypes.arrayOf(PropTypes.object),
}

export const mapStateToProps = (state) => {
  const user = getUser(state)
  return {
    user,
    pages: dataManagementPages(user, getElasticsearchEnabled(state)),
  }
}

export default connect(mapStateToProps)(DataManagement)
