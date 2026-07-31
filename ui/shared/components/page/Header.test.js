import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { LOCAL_LOGIN_URL } from 'shared/utils/constants'
import { PageHeaderComponent } from './Header'

configure({ adapter: new Adapter() })

const USER = {
  date_joined: '2015-02-19T20:22:50.633Z',
  email: 'test@broadinstitute.org',
  first_name: '',
  id: 1,
  is_active: true,
  last_login: '2017-03-14T17:44:53.403Z',
  last_name: '',
  username: 'test',
}

test('shallow-render without crashing', () => {
  /*
    user: PropTypes.object.isRequired,
   */

  shallow(<PageHeaderComponent user={USER} />)
})

test('log out is inside the user dropdown rather than a top level menu item', () => {
  const wrapper = shallow(<PageHeaderComponent user={USER} />)

  const logoutLinks = wrapper.findWhere(node => node.prop('href') === '/logout')
  expect(logoutLinks).toHaveLength(1)
  expect(logoutLinks.first().name()).toEqual('DropdownItem')
})

test('logged out users are offered a log in link and no user dropdown', () => {
  const wrapper = shallow(<PageHeaderComponent user={{}} />)

  expect(wrapper.findWhere(node => node.prop('href') === '/logout')).toHaveLength(0)
  expect(wrapper.find('Dropdown')).toHaveLength(0)
  expect(wrapper.findWhere(node => node.prop('href') === LOCAL_LOGIN_URL)).toHaveLength(1)
})
