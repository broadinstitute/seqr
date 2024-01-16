import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch } from 'react-router-dom'

import { getUser, getElasticsearchEnabled } from 'redux/selectors'
import { Error404, Error401 } from 'shared/components/page/Errors'
import { SimplePageHeader } from 'shared/components/page/PageHeaderLayout'

import AddIGV from './components/AddIGV'
import ElasticsearchStatus from './components/ElasticsearchStatus'
import LoadData from './components/LoadData'
import RnaSeq from './components/RnaSeq'
import SampleQc from './components/SampleQc'
import Users from './components/Users'
import PhenotypePrioritization from './components/PhenotypePrioritization'
import WritePedigree from './components/WritePedigree'

const IFRAME_STYLE = { position: 'fixed', left: '0', top: '95px' }

const PM_DATA_MANAGEMENT_PAGES = [
  { path: 'load_data', component: LoadData },
  { path: 'add_igv', component: AddIGV },
]

const DATA_MANAGEMENT_PAGES = [
  ...PM_DATA_MANAGEMENT_PAGES,
  { path: 'sample_qc', component: SampleQc },
  { path: 'rna_seq', component: RnaSeq },
  { path: 'users', component: Users },
  { path: 'write_pedigree', component: WritePedigree },
  { path: 'phenotype_prioritization', component: PhenotypePrioritization },
]

const ES_DATA_MANAGEMENT_PAGES = [
  { path: 'elasticsearch_status', component: ElasticsearchStatus },
  {
    path: 'kibana',
    component: () => <iframe width="100%" height="100%" title="Kibana" style={IFRAME_STYLE} src="/app/kibana" />,
  },
  ...DATA_MANAGEMENT_PAGES,
]

const dataManagementPages = (isDataManager, elasticsearchEnabled) => {
  if (!isDataManager) {
    return PM_DATA_MANAGEMENT_PAGES
  }
  return elasticsearchEnabled ? ES_DATA_MANAGEMENT_PAGES : DATA_MANAGEMENT_PAGES
}

const mapPageHeaderStateToProps = state => ({
  pages: dataManagementPages(getUser(state).isDataManager, getElasticsearchEnabled(state)),
})

export const DataManagementPageHeader = connect(mapPageHeaderStateToProps)(SimplePageHeader)

const DataManagement = ({ match, user, elasticsearchEnabled }) => (
  (user.isDataManager || user.isPm) ? (
    <Switch>
      {dataManagementPages(user.isDataManager, elasticsearchEnabled).map(({ path, params, component }) => (
        <Route key={path} path={`${match.url}/${path}${params || ''}`} component={component} />))}
      <Route exact path={match.url} component={null} />
      <Route component={Error404} />
    </Switch>
  ) : <Error401 />
)

DataManagement.propTypes = {
  user: PropTypes.object,
  match: PropTypes.object,
  elasticsearchEnabled: PropTypes.bool,
}

const mapStateToProps = state => ({
  user: getUser(state),
  elasticsearchEnabled: getElasticsearchEnabled(state),
})

export default connect(mapStateToProps)(DataManagement)
