import React from 'react'
import PropTypes from 'prop-types'
import { Route, Switch } from 'react-router-dom'
import { Header, Grid } from 'semantic-ui-react'

import VariantSearchForm from './components/VariantSearchForm'
import VariantSearchResults from './components/VariantSearchResults'


const VariantSearch = ({ match }) =>
  <Grid>
    <Grid.Row>
      <Grid.Column width={16}>
        <Switch>
          <Route path={`${match.url}/project/:projectGuid`} component={VariantSearchForm} />
          <Route path={`${match.url}/analysis_group/:analysisGroupGuid`} component={VariantSearchForm} />
          <Route path={`${match.url}/family/:familyGuid`} component={VariantSearchForm} />
          <Route path={`${match.url}/:searchHash`} component={VariantSearchForm} />
          {/* TODO once multi-project enabled allow no path*/}
          <Route component={() => <Header size="huge" textAlign="center">Error 404: Page Not Found</Header>} />
        </Switch>
      </Grid.Column>
    </Grid.Row>
    <Switch>
      <Route path={`${match.url}/:entityType/:entityGuid`} component={null} />
      <Route path={`${match.url}/:searchHash`} component={VariantSearchResults} />
    </Switch>
  </Grid>

VariantSearch.propTypes = {
  match: PropTypes.object,
}

export default VariantSearch
