import React from 'react'
import PropTypes from 'prop-types'
import DocumentTitle from 'react-document-title'
import { connect } from 'react-redux'
import { Route, Switch, NavLink } from 'react-router-dom'
import styled from 'styled-components'
import { Grid, Breadcrumb, Popup, Icon, Header, Menu } from 'semantic-ui-react'

import ProjectPageHeader from 'pages/Project/components/PageHeader'
import VariantSearchPageHeader from 'pages/Search/components/PageHeader'
import { DATA_MANAGEMENT_PAGES } from 'pages/DataManagement/DataManagement'
import { REPORT_PAGES } from 'pages/Report/Report'
import { SummaryDataPageHeader } from 'pages/SummaryData/SummaryData'
import { getGenesById } from 'redux/selectors'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import { ButtonLink } from 'shared/components/StyledComponents'
import { snakecaseToTitlecase } from '../../utils/stringUtils'


const PageHeaderRow = styled(Grid.Row)`
  padding: 9px;
  background-color: #F7F7F7;
  max-height: 200px;
  border-bottom: 1px solid #EEEEEE;
`

const BreadcrumbContainer = styled.div`
  margin: 50px 0px 25px 0px;
  
  .section {
    margin-bottom: 10px !important;
  }
  
  a.active {
    color: #111 !important;
    cursor: auto !important;
  }
`

export const PageHeaderLayout = React.memo(({
  entity, entityGuid, breadcrumb, breadcrumbId, breadcrumbIdSections, title, header, entityLinkPath, entityGuidLinkPath,
  entityLinks, button, description,
}) => {
  let breadcrumbSections = [
    { content: snakecaseToTitlecase(entity), link: entityLinkPath === undefined ? `/${entity}` : entityLinkPath },
  ]
  if (entityGuid) {
    breadcrumbSections.push(
      { content: title || entityGuid, link: `/${entity}/${entityGuid}${entityGuidLinkPath ? `/${entityGuidLinkPath}` : ''}` },
    )
  }
  if (breadcrumbIdSections) {
    breadcrumbSections = breadcrumbSections.concat(breadcrumbIdSections)
  } else if (breadcrumb) {
    breadcrumbSections.push({
      content: snakecaseToTitlecase(breadcrumb),
      link: `/${entity}/${entityGuid}/${breadcrumb}`,
    })
    if (breadcrumbId) {
      const breadcrumbIds = breadcrumbId.split('/')
      breadcrumbSections = breadcrumbSections.concat(breadcrumbIds.map((breadcrumbIdSection, i) => (
        {
          content: breadcrumbIdSection,
          link: `/${entity}/${entityGuid}/${breadcrumb}/${breadcrumbIds.slice(0, i + 1).join('/')}`,
        }
      )))
    }
  }

  const breadcrumbs = breadcrumbSections.reduce(
    (acc, sectionConfig, i, { length }) => {
      if (!sectionConfig.content) {
        return acc
      }
      const sectionProps = sectionConfig.link ?
        { as: NavLink, to: sectionConfig.link, exact: true } : {}
      const section =
        <Breadcrumb.Section key={sectionConfig.content} {...sectionProps} content={sectionConfig.content} />
      if (i && i < length) {
        return [...acc, <Breadcrumb.Divider key={`divider${sectionConfig.content}`} icon="angle double right" />, section]
      }
      return [...acc, section]
    }, [],
  )
  return (
    <PageHeaderRow>
      <DocumentTitle key="title" title={header || `${breadcrumb || 'seqr'}: ${title || snakecaseToTitlecase(entity)}`} />
      <Grid.Column width={1} />
      <Grid.Column width={11}>
        <BreadcrumbContainer>
          <Breadcrumb size="massive">
            {breadcrumbs}
          </Breadcrumb>
        </BreadcrumbContainer>
        {
          description &&
          <div style={{ fontWeight: 300, fontSize: '16px', margin: '0px 30px 20px 5px', display: 'inline-block' }}>
            {description}
          </div>
        }
        {button}
      </Grid.Column>
      <Grid.Column width={3}>
        {entityLinks &&
          <b><br />
            {entityLinks.map(({ popup, content, ...linkProps }) =>
              <div key={content}>
                <ButtonLink as={NavLink} {...linkProps}>{content}</ButtonLink>
                {popup && <Popup content={popup} trigger={<Icon name="question circle outline" color="grey" />} />}
              </div>,
            )}
          </b>
        }
        <br />
        <br />
      </Grid.Column>
      <Grid.Column width={1} />
    </PageHeaderRow>
  )
})

PageHeaderLayout.propTypes = {
  entity: PropTypes.string.isRequired,
  entityGuid: PropTypes.string,
  breadcrumb: PropTypes.string,
  breadcrumbId: PropTypes.string,
  breadcrumbIdSections: PropTypes.array,
  title: PropTypes.string,
  header: PropTypes.string,
  entityLinkPath: PropTypes.string,
  entityGuidLinkPath: PropTypes.string,
  entityLinks: PropTypes.array,
  button: PropTypes.node,
  description: PropTypes.string,
}


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

export const SimplePageHeader = ({ page, pages }) => ([
  <Menu attached key="submenu">
    <Menu.Item key="title">
      <Header size="medium"><HorizontalSpacer width={90} /> {snakecaseToTitlecase(page)} Pages:</Header>
    </Menu.Item>
    {pages.map(({ path }) =>
      <Menu.Item key={path} as={NavLink} to={`/${page}/${path}`}>{snakecaseToTitlecase(path)}</Menu.Item>,
    )}
  </Menu>,
  <VerticalSpacer height={20} key="spacer" />,
])

SimplePageHeader.propTypes = {
  page: PropTypes.string,
  pages: PropTypes.array,
}

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
