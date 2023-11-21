import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch } from 'react-router-dom'

import { getUser, getElasticsearchEnabled } from 'redux/selectors'
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
import SampleMetadata from './components/SampleMetadata'
import VariantLookup from './components/VariantLookup'

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
  { path: 'sample_metadata', params: '/:projectGuid?', component: SampleMetadata },
  { path: 'hpo_terms', component: Hpo },
  { path: 'matchmaker', component: Matchmaker },
]

const NO_ES_PAGES = [{ path: 'variant_lookup', component: VariantLookup }]

const SUMMARY_DATA_NO_ES_PAGES = [
  ...NO_ES_PAGES,
  ...SUMMARY_DATA_PAGES,
]

const ANALYST_SUMMARY_DATA_PAGES = [
  ...SUMMARY_DATA_PAGES,
  { path: 'success_story', params: '/:successStoryTypes?', component: SuccessStory },
  { path: 'external_analysis', component: ExternalAnalysis },
]

const ANALYST_SUMMARY_DATA_NO_ES_PAGES = [
  ...NO_ES_PAGES,
  ...ANALYST_SUMMARY_DATA_PAGES,
]

const getPages = ({ user, elasticsearchEnabled }) => {
  if (elasticsearchEnabled) {
    return user.isAnalyst ? ANALYST_SUMMARY_DATA_PAGES : SUMMARY_DATA_PAGES
  }
  return user.isAnalyst ? ANALYST_SUMMARY_DATA_NO_ES_PAGES : SUMMARY_DATA_NO_ES_PAGES
}

const BaseSummaryDataPageHeader = ({ match, ...props }) => (
  <SimplePageHeader page="summary_data" subPage={match.params.subPage} pages={getPages(props)} />)

BaseSummaryDataPageHeader.propTypes = {
  user: PropTypes.object,
  match: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
  elasticsearchEnabled: getElasticsearchEnabled(state),
})

export const SummaryDataPageHeader = connect(mapStateToProps)(BaseSummaryDataPageHeader)

const SummaryData = ({ match, ...props }) => (
  <Switch>
    {getPages(props).map(
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
