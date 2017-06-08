import React from 'react'
import { shallow } from 'enzyme'
import { BaseLayoutComponent } from './BaseLayout'


test('shallow-render without crashing', () => {
  /*
    user: PropTypes.object.isRequired,
    children: PropTypes.node,
   */

  const props = {
    user: {
      date_joined: '2015-02-19T20:22:50.633Z',
      email: 'test@broadinstitute.org',
      first_name: '',
      id: 1,
      is_active: true,
      is_staff: true,
      last_login: '2017-03-14T17:44:53.403Z',
      last_name: '',
      username: 'test',
    },
    children: [],
  }

  shallow(<BaseLayoutComponent {...props} />)
})
