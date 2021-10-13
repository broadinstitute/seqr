import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch } from 'react-router-dom'

import ProjectPageHeader from 'pages/Project/components/PageHeader'
import VariantSearchPageHeader from 'pages/Search/components/PageHeader'
import { DATA_MANAGEMENT_PAGES } from 'pages/DataManagement/DataManagement'
import { REPORT_PAGES } from 'pages/Report/Report'
import { SummaryDataPageHeader } from 'pages/SummaryData/SummaryData'
import { getGenesById } from 'redux/selectors'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import { ButtonLink } from 'shared/components/StyledComponents'
import { PageHeaderLayout, SimplePageHeader } from './PageHeaderLayout'

const BaseGenePageHeader = React.memo(({ gene, match }) =>
  <PageHeaderLayout
    entity="gene_info"
    entityGuid={match.params.geneId}
    title={match.params.geneId && (gene ? gene.geneSymbol : match.params.geneId)}
  />,
)

BaseGenePageHeader.propTypes = {
  gene: PropTypes.object,
  match: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  gene: getGenesById(state)[ownProps.match.params.geneId],
})

export const GenePageHeader = connect(mapStateToProps)(BaseGenePageHeader)

const NO_HEADER_PAGES = [
  '/dashboard', '/create_project_from_workspace', '/workspace', '/users', '/login', '/matchmaker', '/privacy_policy',
  '/terms_of_service', '/accept_policies',
]

const SIMPLE_HEADER_PAGES = [
  { page: 'data_management', pages: DATA_MANAGEMENT_PAGES },
  { page: 'report', pages: REPORT_PAGES },
]

export default () =>
  <Switch>
    {NO_HEADER_PAGES.map(page =>
      <Route key={page} path={page} component={() => null} />,
    )}
    {SIMPLE_HEADER_PAGES.map(({ page, ...props }) =>
      <Route key={page} path={`/${page}`} component={() => <SimplePageHeader page={page} {...props} />} />,
    )}
    <Route path="/project/:projectGuid/saved_variants/:variantPage?/:breadcrumbId?/:tag?" component={({ match }) => <ProjectPageHeader match={match} breadcrumb="saved_variants" />} />
    <Route path="/project/:projectGuid/:breadcrumb/:breadcrumbId?/:breadcrumbIdSection*" component={ProjectPageHeader} />
    <Route path="/summary_data" component={SummaryDataPageHeader} />
    <Route path="/variant_search/:pageType/:entityGuid" component={VariantSearchPageHeader} />
    <Route path="/:entity/:entityGuid?/:breadcrumb?/:breadcrumbId*" component={({ match }) => <PageHeaderLayout {...match.params} />} />
  </Switch>
