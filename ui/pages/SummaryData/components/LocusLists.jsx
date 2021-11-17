import React from 'react'
import PropTypes from 'prop-types'
import { Route, Switch } from 'react-router-dom'
import { Container } from 'semantic-ui-react'

import { CreateLocusListButton } from 'shared/components/buttons/LocusListButtons'
import LocusListDetailPanel from 'shared/components/panel/genes/LocusListDetail'
import { LocusListsLoader } from 'shared/components/LocusListLoader'
import LocusListTables from 'shared/components/table/LocusListTables'

const LOCUS_LIST_TABLE_BUTTONS = { My: <CreateLocusListButton /> }

const LocusListTablePage = () => <LocusListTables tableButtons={LOCUS_LIST_TABLE_BUTTONS} />

const LocusListDetail = ({ match }) => <LocusListDetailPanel locusListGuid={match.params.locusListGuid} />
LocusListDetail.propTypes = {
  match: PropTypes.object,
}

const LocusLists = ({ match }) => (
  <LocusListsLoader>
    <Container>
      <Switch>
        <Route path={`${match.url}/:locusListGuid`} component={LocusListDetail} />
        <Route path={`${match.url}`} component={LocusListTablePage} />
      </Switch>
    </Container>
  </LocusListsLoader>
)

LocusLists.propTypes = {
  match: PropTypes.object,
}

export default LocusLists
