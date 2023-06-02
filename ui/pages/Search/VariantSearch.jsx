import React from 'react'
import PropTypes from 'prop-types'
import { Route, Switch } from 'react-router-dom'
import { Grid } from 'semantic-ui-react'

import { Error404 } from 'shared/components/page/Errors'
import VariantSearchForm, { NoEditProjectsVariantSearchForm } from './components/VariantSearchForm'
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

const VariantSearch = ({ match }) => (
  <Grid>
    <Grid.Row>
      <Grid.Column width={16}>
        <Switch>
          <Route path={SEARCH_FORM_PAGES.map(pagePath => `${match.url}/${pagePath}`)} component={VariantSearchForm} />
          <Route path={`${match.url}/families/:families`} component={NoEditProjectsVariantSearchForm} />
          <Route path={`${match.url}/${SINGLE_VARIANT_RESULTS_PATH}`} />
          <Route path={match.url} exact component={VariantSearchForm} />
          <Route component={Error404} />
        </Switch>
      </Grid.Column>
    </Grid.Row>
    <Switch>
      {SEARCH_RESULTS_PAGES.map(
        pagePath => <Route key={pagePath} path={`${match.url}/${pagePath}`} component={VariantSearchResults} />,
      )}
    </Switch>
  </Grid>
)

VariantSearch.propTypes = {
  match: PropTypes.object,
}

export default VariantSearch
