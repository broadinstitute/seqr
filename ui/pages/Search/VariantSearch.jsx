import React from 'react'
import PropTypes from 'prop-types'
import { Route, Switch } from 'react-router-dom'
import { Header, Grid } from 'semantic-ui-react'

import VariantSearchForm from './components/VariantSearchForm'
import VariantSearchResults from './components/VariantSearchResults'

const RESULTS_PATH = 'results/:searchHash'
const SINGLE_VARIANT_RESULTS_PATH = 'variant/:variantId/family/:familyGuid'

const SEARCH_FORM_PAGES = [
  'project/:projectGuid',
  'analysis_group/:analysisGroupGuid',
  'family/:familyGuid',
  RESULTS_PATH,
]

const SEARCH_RESULTS_PAGES = [
  RESULTS_PATH,
  SINGLE_VARIANT_RESULTS_PATH,
]

const VariantSearch = ({ match }) =>
  <Grid>
    <Grid.Row>
      <Grid.Column width={16}>
        <Switch>
          {SEARCH_FORM_PAGES.map(pagePath =>
            <Route key={pagePath} path={`${match.url}/${pagePath}`} component={VariantSearchForm} />,
          )}
          <Route path={`${match.url}/${SINGLE_VARIANT_RESULTS_PATH}`} />,
          <Route path={match.url} exact component={VariantSearchForm} />,
          <Route component={() => <Header size="huge" textAlign="center">Error 404: Page Not Found</Header>} />
        </Switch>
      </Grid.Column>
    </Grid.Row>
    <Switch>
      {SEARCH_RESULTS_PAGES.map(pagePath =>
        <Route key={pagePath} path={`${match.url}/${pagePath}`} component={VariantSearchResults} />,
      )}
    </Switch>
  </Grid>

VariantSearch.propTypes = {
  match: PropTypes.object,
}

export default VariantSearch
