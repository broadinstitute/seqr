import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { NavLink, Route, Switch } from 'react-router-dom'
import { Header, Menu } from 'semantic-ui-react'

import { getUser } from 'redux/selectors'
import { Error404, Error401 } from 'shared/components/page/Errors'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'

import Anvil from './components/Anvil'
import CustomSearch from './components/CustomSearch'
import DiscoverySheet from './components/DiscoverySheet'
import SuccessStory from './components/SuccessStory'
import ElasticsearchStatus from './components/ElasticsearchStatus'
import Matchmaker from './components/Matchmaker'
import SampleMetadata from './components/SampleMetadata'
import SampleQc from './components/SampleQc'
import SavedVariants from './components/SavedVariants'
import SeqrStats from './components/SeqrStats'
import Users from './components/Users'

const IFRAME_STYLE = { position: 'fixed', left: '0', top: '95px' }

const ANALYST_PAGES = [
  { path: 'anvil', component: Anvil },
  { path: 'custom_search', params: '/:searchHash?', component: CustomSearch },
  { path: 'discovery_sheet', params: '/:projectGuid?', component: DiscoverySheet },
  { path: 'success_story', params: '/:successStoryTypes?', component: SuccessStory },
  { path: 'matchmaker', component: Matchmaker },
  { path: 'sample_metadata', params: '/:projectGuid?', component: SampleMetadata },
  { path: 'saved_variants', component: SavedVariants },
  { path: 'seqr_stats', component: SeqrStats },
]

const DATA_MANAGER_PAGES = [
  { path: 'elasticsearch_status', component: ElasticsearchStatus },
  { path: 'kibana', component: () => <iframe width="100%" height="100%" style={IFRAME_STYLE} src="/app/kibana" /> },
  { path: 'sample_qc', component: SampleQc },
]

const SUPERUSER_PAGES = [
  { path: 'users', component: Users },
]

export const BaseStaffPageHeader = ({ user }) =>
  <Menu attached>
    <Menu.Item><Header size="medium"><HorizontalSpacer width={90} /> Staff Pages:</Header></Menu.Item>
    {user.isAnalyst && ANALYST_PAGES.map(({ path }) =>
      <Menu.Item key={path} as={NavLink} to={`/staff/${path}`}>{snakecaseToTitlecase(path)}</Menu.Item>,
    )}
    {user.isDataManager && DATA_MANAGER_PAGES.map(({ path }) =>
      <Menu.Item key={path} as={NavLink} to={`/staff/${path}`}>{snakecaseToTitlecase(path)}</Menu.Item>,
    )}
    {user.isSuperuser && SUPERUSER_PAGES.map(({ path }) =>
      <Menu.Item key={path} as={NavLink} to={`/staff/${path}`}>{snakecaseToTitlecase(path)}</Menu.Item>,
    )}
  </Menu>

BaseStaffPageHeader.propTypes = {
  user: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
})

export const StaffPageHeader = connect(mapStateToProps)(BaseStaffPageHeader)

const Forbidden = () => <Error401 />

// TODO break this into different menu items? new URLs?
const Staff = ({ match, user }) => (
  (user.isSuperuser || user.isAnalyst || user.isDataManager) ? (
    <div>
      <VerticalSpacer height={20} />
      <Switch>
        {ANALYST_PAGES.map(({ path, params, component }) =>
          <Route key={path} path={`${match.url}/${path}${params || ''}`} component={user.isAnalyst ? component : Forbidden} />,
        )}
        {DATA_MANAGER_PAGES.map(({ path, params, component }) =>
          <Route key={path} path={`${match.url}/${path}${params || ''}`} component={user.isDataManager ? component : Forbidden} />,
        )}
        {SUPERUSER_PAGES.map(({ path, params, component }) =>
          <Route key={path} path={`${match.url}/${path}${params || ''}`} component={user.isSuperuser ? component : Forbidden} />,
        )}
        <Route path={match.url} component={null} />
        <Route component={() => <Error404 />} />
      </Switch>
    </div>
  ) : <Error401 />
)

Staff.propTypes = {
  user: PropTypes.object,
  match: PropTypes.object,
}


export default connect(mapStateToProps)(Staff)
