import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch } from 'react-router-dom'

import { getUser } from 'redux/selectors'
import { Error404 } from 'shared/components/page/Errors'
import { SimplePageHeader } from 'shared/components/page/PageHeaderLayout'
import GeneDetail from 'shared/components/panel/genes/GeneDetail'

import SuccessStory from './components/SuccessStory'
import Matchmaker from './components/Matchmaker'
import SavedVariants from './components/SavedVariants'
import GeneInfoSearch from './components/GeneInfoSearch'
import LocusLists from './components/LocusLists'
import ExternalAnalysis from './components/ExternalAnalysis'
import Hpo from './components/Hpo'

const GenePage = ({ match }) => (
  match.params.geneId ? <GeneDetail geneId={match.params.geneId} /> : <GeneInfoSearch />
)

GenePage.propTypes = {
  match: PropTypes.object,
}

const SUMMARY_DATA_PAGES = [
  { path: 'gene_info', params: '/:geneId?', component: GenePage },
  { path: 'gene_lists', component: LocusLists },
  { path: 'saved_variants', component: SavedVariants },
  { path: 'hpo_terms', component: Hpo },
  { path: 'matchmaker', component: Matchmaker },
]

const ANALYST_SUMMARY_DATA_PAGES = [
  ...SUMMARY_DATA_PAGES,
  { path: 'success_story', params: '/:successStoryTypes?', component: SuccessStory },
  { path: 'external_analysis', component: ExternalAnalysis },
]

const BaseSummaryDataPageHeader = ({ user, match }) => (
  <SimplePageHeader page="summary_data" subPage={match.params.subPage} pages={user.isAnalyst ? ANALYST_SUMMARY_DATA_PAGES : SUMMARY_DATA_PAGES} />)

BaseSummaryDataPageHeader.propTypes = {
  user: PropTypes.object,
  match: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export const SummaryDataPageHeader = connect(mapStateToProps)(BaseSummaryDataPageHeader)

const SummaryData = ({ match, user }) => (
  <Switch>
    {(user.isAnalyst ? ANALYST_SUMMARY_DATA_PAGES : SUMMARY_DATA_PAGES).map(
      ({ path, params, component }) => <Route key={path} path={`${match.url}/${path}${params || ''}`} component={component} />,
    )}
    <Route path={match.url} component={null} />
    <Route component={Error404} />
  </Switch>
)

SummaryData.propTypes = {
  user: PropTypes.object,
  match: PropTypes.object,
}

export default connect(mapStateToProps)(SummaryData)
