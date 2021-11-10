import React from 'react'
import PropTypes from 'prop-types'
import DocumentTitle from 'react-document-title'
import { NavLink } from 'react-router-dom'
import styled from 'styled-components'
import { Grid, Breadcrumb, Popup, Icon, Header, Menu } from 'semantic-ui-react'

import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import { ButtonLink, InlineHeader } from 'shared/components/StyledComponents'
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

const PageHeaderLayout = React.memo(({
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
        {description && <InlineHeader size="large" subheader={description} />}
        {button}
      </Grid.Column>
      <Grid.Column width={3}>
        {entityLinks && (
          <b>
            <br />
            {entityLinks.map(({ popup, content, ...linkProps }) => (
              <div key={content}>
                <ButtonLink as={NavLink} {...linkProps}>{content}</ButtonLink>
                {popup && <Popup content={popup} trigger={<Icon name="question circle outline" color="grey" />} />}
              </div>
            ))}
          </b>
        )}
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
  breadcrumbIdSections: PropTypes.arrayOf(PropTypes.object),
  title: PropTypes.string,
  header: PropTypes.string,
  entityLinkPath: PropTypes.string,
  entityGuidLinkPath: PropTypes.string,
  entityLinks: PropTypes.arrayOf(PropTypes.object),
  button: PropTypes.node,
  description: PropTypes.string,
}

export default PageHeaderLayout

export const SimplePageHeader = ({ page, pages }) => ([
  <Menu attached key="submenu">
    <Menu.Item key="title">
      <Header size="medium">
        <HorizontalSpacer width={90} />
        {`${snakecaseToTitlecase(page)} Pages:`}
      </Header>
    </Menu.Item>
    {pages.map(
      ({ path }) => <Menu.Item key={path} as={NavLink} to={`/${page}/${path}`}>{snakecaseToTitlecase(path)}</Menu.Item>,
    )}
  </Menu>,
  <VerticalSpacer height={20} key="spacer" />,
])

SimplePageHeader.propTypes = {
  page: PropTypes.string,
  pages: PropTypes.arrayOf(PropTypes.object),
}
