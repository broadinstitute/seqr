import React from 'react'
import PropTypes from 'prop-types'
import { Route, Switch } from 'react-router-dom'
import { Container } from 'semantic-ui-react'

import { CreateLocusListButton } from 'shared/components/buttons/LocusListButtons'
import LocusListDetailPanel from 'shared/components/panel/genes/LocusListDetail'
import { LocusListsLoader } from 'shared/components/LocusListLoader'
import LocusListTables from 'shared/components/table/LocusListTables'


const LOCUS_LIST_TABLE_BUTTONS = { My: <CreateLocusListButton /> }

const LocusLists = ({ match }) =>
  <LocusListsLoader>
    <Container>
      <Switch>
        <Route path={`${match.url}/:locusListGuid`} component={props => <LocusListDetailPanel locusListGuid={props.match.params.locusListGuid} />} />
        <Route path={`${match.url}`} component={() => <LocusListTables tableButtons={LOCUS_LIST_TABLE_BUTTONS} />} />
      </Switch>
    </Container>
  </LocusListsLoader>

LocusLists.propTypes = {
  match: PropTypes.object,
}

export default LocusLists
