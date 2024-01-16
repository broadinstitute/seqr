import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch } from 'react-router-dom'

import { getUser } from 'redux/selectors'
import { Error404, Error401 } from 'shared/components/page/Errors'

import Anvil from './components/Anvil'
import CustomSearch from './components/CustomSearch'
import FamilyMetadata from './components/FamilyMetadata'
import Gregor from './components/Gregor'
import SeqrStats from './components/SeqrStats'
import VariantMetadata from './components/VariantMetadata'

export const REPORT_PAGES = [
  { path: 'anvil', component: Anvil },
  { path: 'custom_search', params: '/:searchHash?', component: CustomSearch },
  { path: 'family_metadata', params: '/:projectGuid?', component: FamilyMetadata },
  { path: 'variant_metadata', params: '/:projectGuid?', component: VariantMetadata },
  { path: 'gregor', component: Gregor },
  { path: 'seqr_stats', component: SeqrStats },
]

const Report = ({ match, user }) => (
  user.isAnalyst ? (
    <Switch>
      {REPORT_PAGES.map(
        ({ path, params, component }) => <Route key={path} path={`${match.url}/${path}${params || ''}`} component={component} />,
      )}
      <Route path={match.url} component={null} />
      <Route component={Error404} />
    </Switch>
  ) : <Error401 />
)

Report.propTypes = {
  user: PropTypes.object,
  match: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(Report)
