import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch } from 'react-router-dom'

import ProjectPageHeader from 'pages/Project/components/PageHeader'
import VariantSearchPageHeader from 'pages/Search/components/PageHeader'
import { DataManagementPageHeader } from 'pages/DataManagement/DataManagement'
import { REPORT_PAGES } from 'pages/Report/Report'
import { SummaryDataPageHeader } from 'pages/SummaryData/SummaryData'
import { getGenesById } from 'redux/selectors'
import { PUBLIC_PAGES } from 'shared/utils/constants'
import PageHeaderLayout, { SimplePageHeader, useSeqrTitle } from './PageHeaderLayout'

const BaseGenePageHeader = React.memo(({ gene, match }) => (
  <PageHeaderLayout
    entity="gene_info"
    entityGuid={match.params.geneId}
    title={match.params.geneId && (gene ? gene.geneSymbol : match.params.geneId)}
  />
))

BaseGenePageHeader.propTypes = {
  gene: PropTypes.object,
  match: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  gene: getGenesById(state)[ownProps.match.params.geneId],
})

export const GenePageHeader = connect(mapStateToProps)(BaseGenePageHeader)

const NO_HEADER_PAGES = [
  '/dashboard', '/create_project_from_workspace', '/workspace', '/users', '/login', '/accept_policies', ...PUBLIC_PAGES,
]

const NO_HEADER_PAGE_TITLES = {
  '': 'Dashboard',
  create_project_from_workspace: 'Load Data',
}

const SIMPLE_HEADER_PAGES = [
  { page: 'data_management', component: DataManagementPageHeader },
  { page: 'report', pages: REPORT_PAGES },
].map(({ page, component, ...props }) => ({
  key: page,
  path: `/${page}/:subPage?`,
  component: ({ match }) => React.createElement(
    component || SimplePageHeader, { page, subPage: match.params.subPage, ...props },
  ),
}))

const EmptyHeader = ({ match }) => {
  const page = match.path.split('/').pop()
  useSeqrTitle(NO_HEADER_PAGE_TITLES[page] || page)

  return null
}

const noHeaderRoute = page => <Route key={page} path={page} component={EmptyHeader} />

const simpleHeaderRoute = props => <Route {...props} />

const ProjectSavedVariantsPageHeader = ({ match }) => <ProjectPageHeader match={match} breadcrumb="saved_variants" />
ProjectSavedVariantsPageHeader.propTypes = {
  match: PropTypes.object,
}

const DefaultPageHeaderLayout = ({ match }) => <PageHeaderLayout {...match.params} />
DefaultPageHeaderLayout.propTypes = {
  match: PropTypes.object,
}

export default () => (
  <Switch>
    <Route exact path="/" component={EmptyHeader} />
    {NO_HEADER_PAGES.map(noHeaderRoute)}
    {SIMPLE_HEADER_PAGES.map(simpleHeaderRoute)}
    <Route path="/project/:projectGuid/saved_variants/:variantPage?/:breadcrumbId?/:tag?" component={ProjectSavedVariantsPageHeader} />
    <Route path="/project/:projectGuid/:breadcrumb/:breadcrumbId?/:breadcrumbIdSection?/:breadcrumbIdSubsection*" component={ProjectPageHeader} />
    <Route path="/summary_data/:subPage?" component={SummaryDataPageHeader} />
    <Route path="/variant_search/:pageType/:entityGuid" component={VariantSearchPageHeader} />
    <Route path="/:entity/:entityGuid?/:breadcrumb?/:breadcrumbId*" component={DefaultPageHeaderLayout} />
  </Switch>
)
