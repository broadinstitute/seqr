import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch } from 'react-router-dom'
import { Container } from 'semantic-ui-react'

import { getLocusListsByGuid } from 'redux/selectors'
import { CreateLocusListButton, DeleteLocusListButton } from 'shared/components/buttons/LocusListButtons'
import { PageHeaderLayout } from 'shared/components/page/PageHeader'
import LocusListDetailPanel from 'shared/components/panel/genes/LocusListDetail'
import { LocusListsLoader } from 'shared/components/LocusListLoader'
import LocusListTables from 'shared/components/table/LocusListTables'

const originalLocusListPage = locusList => [{ path: locusList ? `${locusList.locusListGuid}?guid=true` : '' }]

const PageHeader = ({ locusList }) =>
  <PageHeaderLayout
    entity="gene_lists"
    entityGuid={locusList && locusList.locusListGuid}
    title={locusList && locusList.name}
    description={!locusList && 'This page shows all of the gene lists that are available in your account'}
    button={locusList ? <DeleteLocusListButton locusList={locusList} /> : <CreateLocusListButton />}
    originalPagePath="gene-lists"
    originalPages={originalLocusListPage(locusList)}
  />

PageHeader.propTypes = {
  locusList: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  locusList: getLocusListsByGuid(state)[ownProps.match.params.locusListGuid],
})

export const LocusListPageHeader = connect(mapStateToProps)(PageHeader)

const LocusLists = ({ match }) =>
  <LocusListsLoader>
    <Container>
      <Switch>
        <Route path={`${match.url}/:locusListGuid`} component={props => <LocusListDetailPanel locusListGuid={props.match.params.locusListGuid} />} />
        <Route path={`${match.url}`} component={LocusListTables} />
      </Switch>
    </Container>
  </LocusListsLoader>

LocusLists.propTypes = {
  match: PropTypes.object,
}

export default LocusLists
