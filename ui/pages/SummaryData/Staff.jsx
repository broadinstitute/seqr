import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { NavLink, Route, Switch } from 'react-router-dom'
import { Header, Menu } from 'semantic-ui-react'

import { getUser } from 'redux/selectors'
import { Error404, Error401 } from 'shared/components/page/Errors'
import { HorizontalSpacer, VerticalSpacer } from 'shared/components/Spacers'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'

import SuccessStory from './components/SuccessStory'
import Matchmaker from './components/Matchmaker'
import SavedVariants from './components/SavedVariants'

const IFRAME_STYLE = { position: 'fixed', left: '0', top: '95px' }

const STAFF_PAGES = [
  { path: 'saved_variants', component: SavedVariants },
  { path: 'success_story', params: '/:successStoryTypes?', component: SuccessStory },
  { path: 'matchmaker', component: Matchmaker },
]

export const StaffPageHeader = () =>
  <Menu attached>
    <Menu.Item><Header size="medium"><HorizontalSpacer width={90} /> Staff Pages:</Header></Menu.Item>
    {STAFF_PAGES.map(({ path }) =>
      <Menu.Item key={path} as={NavLink} to={`/staff/${path}`}>{snakecaseToTitlecase(path)}</Menu.Item>,
    )}
  </Menu>

const Staff = ({ match, user }) => (
  user.isStaff ? (
    <div>
      <VerticalSpacer height={20} />
      <Switch>
        {STAFF_PAGES.map(({ path, params, component }) =>
          <Route key={path} path={`${match.url}/${path}${params || ''}`} component={component} />,
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

const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(Staff)
